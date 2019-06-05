from __future__ import print_function
"""
pytrace.py
"""

import cStringIO
import os
import struct
import sys

# TODO: Two kinds of tracing?
# - FullTracer -> Chrome trace?
# - ReservoirSamplingTracer() -- flame graph that is deterministic?

# TODO: Check this in but just go ahead and fix wild.sh instead.


class Tracer(object):
  # Limit to 10M events by default.
  def __init__(self, max_events=10e6):
    self.pid = os.getpid()
    # append
    self.event_strs = cStringIO.StringIO()

    # After max_events we stop recording
    self.max_events = max_events
    self.num_events = 0
    self.depth = 0

  # Python VM callback
  def OnEvent(self, frame, event_type, arg):
    # Test overhead
    # 7.5 seconds.  Geez.  That's crazy high.
    # The baseline is 2.7 seconds, and _lsprof takes 3.8 seconds.

    # I guess that's why pytracing is a decorator and only works on one part of
    # the program.
    # pytracing isn't usable with large programs.  It can't run abuild -h.

    # What I really want is the nicer visualization.  I don't want the silly
    # cProfile output.

    self.num_events += 1
    name = frame.f_code.co_name
    filename = frame.f_code.co_filename
    if event_type in ('call', 'c_call'):
      self.depth += 1

    record = '%s%s\t%s\t%s\t%s\t%s\n' % ('  ' * self.depth,
        event_type, filename, frame.f_lineno, name, arg)
    self.event_strs.write(record)

    if event_type in ('return', 'c_return'):
      self.depth -= 1

    return

    # NOTE:  Do we want a struct.pack version eventually?
    #self.event_strs.write('')

  def Start(self):
    sys.setprofile(self.OnEvent)

  def Stop(self, path):
    sys.setprofile(None)
    # Only one process should write out the file!
    if os.getpid() != self.pid:
      return

    # TODO:
    # - report number of events?
    # - report number of bytes?
    print('num_events: %d' % self.num_events, file=sys.stderr)
    print('Writing to %r' % path, file=sys.stderr)
    with open(path, 'w') as f:
      f.write(self.event_strs.getvalue())


def main(argv):
  t = Tracer()
  import urlparse
  t.Start()
  print(urlparse.urlparse('http://example.com/foo'))
  t.Stop('demo.pytrace')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
