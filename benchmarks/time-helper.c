#define _GNU_SOURCE  // for timersub()
#include <assert.h>
#include <errno.h>
#include <getopt.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>        // exit()
#include <sys/resource.h>  // getrusage()
#include <sys/time.h>
#include <sys/wait.h>
#include <unistd.h>

void die_errno(const char *message) {
  perror(message);
  exit(1);
}

void die(const char *message) {
  fprintf(stderr, "time-helper: %s\n", message);
  exit(1);
}

typedef struct Spec_t {
  char *out_path;
  bool append;

  char delimiter;  // delimiter should be tab or ,
  bool verbose;    // whether to show verbose logging

  bool x;  // %x status
  bool e;  // %e elapsed
  bool y;  // start time
  bool z;  // end time
  bool U;  // %U user time
  bool S;  // %S system time
  bool M;  // %M maxrss
  bool m;  // page faults, context switches, etc.
  int argc;
  char **argv;
} Spec;

// Write CSV/TSV cells of different types
void int_cell(FILE *f, char delimiter, int val) {
  if (delimiter != 0) {  // NUL is invalid delimiter
    fprintf(f, "%c%d", delimiter, val);
  } else {
    fprintf(f, "%d", val);
  }
}

void time_cell(FILE *f, char delimiter, struct timeval *val) {
  fprintf(f, "%c%ld.%06ld", delimiter, val->tv_sec, val->tv_usec);
}

int time_helper(Spec *spec, FILE *f) {
  char *prog = spec->argv[0];

  struct timeval start;
  struct timeval end;

  int status = 0;
  switch (fork()) {
  case -1:
    die_errno("fork");
    break;

  case 0:  // child exec
    if (execvp(prog, spec->argv) < 0) {
      fprintf(stderr, "time-helper: error executing '%s'\n", prog);
      die_errno("execvp");
    }
    assert(0);  // execvp() never returns

  default:  // parent measures elapsed time of child
    if (gettimeofday(&start, NULL) < 0) {
      die_errno("gettimeofday");
    }
    wait(&status);
    if (gettimeofday(&end, NULL) < 0) {
      die_errno("gettimeofday");
    }
    break;
  }
  // fprintf(stderr, "done waiting\n");

  struct timeval elapsed;
  timersub(&end, &start, &elapsed);

  struct rusage usage;
  getrusage(RUSAGE_CHILDREN, &usage);

  // struct timeval *user = &usage.ru_utime;
  // struct timeval *sys = &usage.ru_stime;

  // this is like the definition of $? that shell use
  int exit_status = -1;
  if (WIFEXITED(status)) {
    exit_status = WEXITSTATUS(status);
  } else if (WIFSIGNALED(status)) {
    exit_status = 128 + WTERMSIG(status);
  } else {
    // We didn't pass WUNTRACED, so normally we won't get this.  But ptrace()
    // will get here.
    ;
  }

  char d = spec->delimiter;
  // NO delimiter at first!
  if (spec->x) {
    int_cell(f, 0, exit_status);
  }
  if (spec->e) {
    time_cell(f, d, &elapsed);
  }
  if (spec->y) {
    time_cell(f, d, &start);
  }
  if (spec->z) {
    time_cell(f, d, &end);
  }
  if (spec->U) {
    time_cell(f, d, &usage.ru_utime);
  }
  if (spec->S) {
    time_cell(f, d, &usage.ru_stime);
  }
  if (spec->M) {
    int_cell(f, d, usage.ru_maxrss);
  }
  if (spec->m) {
    int_cell(f, d, usage.ru_minflt);
    int_cell(f, d, usage.ru_majflt);
    int_cell(f, d, usage.ru_nswap);
    int_cell(f, d, usage.ru_inblock);
    int_cell(f, d, usage.ru_oublock);
    int_cell(f, d, usage.ru_nsignals);
    int_cell(f, d, usage.ru_nvcsw);
    int_cell(f, d, usage.ru_nivcsw);
  }

  return exit_status;
}

int main(int argc, char **argv) {
  Spec spec = {0};

  spec.out_path = "/dev/null";  // default value

  // http://www.gnu.org/software/libc/manual/html_node/Example-of-Getopt.html
  // + means to be strict about flag parsing.
  int c;
  while ((c = getopt(argc, argv, "+o:ad:vxeyzUSMm")) != -1) {
    switch (c) {
    case 'o':
      spec.out_path = optarg;
      break;
    case 'a':
      spec.append = true;
      break;

    case 'd':
      spec.delimiter = optarg[0];
      break;
    case 'v':
      spec.verbose = true;
      break;

    case 'x':
      spec.x = true;
      break;
    case 'e':
      spec.e = true;
      break;
    case 'y':
      spec.y = true;
      break;
    case 'z':
      spec.z = true;
      break;

      // --rusage
    case 'U':
      spec.U = true;
      break;
    case 'S':
      spec.S = true;
      break;
    case 'M':
      spec.M = true;
      break;

    case 'm':  // --rusage-2
      spec.m = true;
      break;

    case '?':  // getopt library will print error
      return 2;

    default:
      abort();  // should never happen
    }
  }

  int a = optind;  // index into argv
  if (a == argc) {
    die("expected a command to run");
  }

  spec.argv = argv + a;
  spec.argc = argc - a;

  char *mode = spec.append ? "a" : "w";
  FILE *f = fopen(spec.out_path, mode);
  int exit_status = time_helper(&spec, f);
  fclose(f);

  return exit_status;
}
