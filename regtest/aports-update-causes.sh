#!bin/ysh
#
# Generate a new report, based on the latest report available.
# Used to update causes in a report without rebuilding any packages.
# 
# Example usage:
#   regtest/aports-update-causes.sh update-latest main # generate new report for main
#   regtest/aports-update-causes.sh update-latest community # generate new report for community

const REPORTS_PATH="_tmp/aports-report"

proc stdout_to_stderr() {
  exec 3>&1
  exec 1>&2
}

proc restore_stdout() {
  exec 1>&3
  exec 3>&-
}
  
func useMainReports(kind) {
  if(kind === 'main') {
    return (true)
  }
  return (false)
}

func useCommunityReports(kind) {
  if (kind === 'community') {
    return (true)
  }
  return (false)
}

func calculateNewEpoch(use_main) {
  var new_epoch = $(date +%Y-%m-%d)
  if (use_main === false) {
    setvar new_epoch = new_epoch ++ "-comm"
  }
  return (new_epoch ++ "-cause")
}

proc get-last-epoch(use_main) {
  var last_epoch = ""
  var additional_grep = ""
  if (use_main === 'true') {
    setvar additional_grep = " | grep -v comm "
  } else {
    setvar additional_grep = " | grep comm "
  }
  setvar last_epoch = $(ssh oils@op.oils.pub "ls /home/oils/op.oils.pub/aports-build | grep .wwz $additional_grep | sort -r | head -n 1")
  setvar last_epoch = ${last_epoch%.wwz}
  echo $last_epoch
}

proc rename-editing-epoch(new_epoch) {
  var pattern = / u'readonly EDITING_APORTS_EPOCH=\'' dot* /
  var new_value = u'readonly EDITING_APORTS_EPOCH=\'' ++ new_epoch ++ u'.wwz\''
  sed -i -E "s/$pattern/$new_value/" regtest/aports-html.sh
}

# adds a new entry with new_epoch right under the entry
# of original_epoch in the html for published.html
proc add-report-entry(original_epoch, new_epoch, use_main) {
  var last_entry = "- [$original_epoch]($original_epoch.wwz/_tmp/aports-report/$original_epoch/diff_merged.html)"
  var entry = "- [$new_epoch]($new_epoch.wwz/_tmp/aports-report/$new_epoch/diff_merged.html)"

  if(use_main === 'false') {
    # indent to indicate partial run, which we are assuming for community for now
    setvar entry = '  ' + entry
  }

  # get the line number of the entry with original_epoch so we can append our line
  var insert_line = $(grep -n -F -- "$last_entry" regtest/aports-html.sh | cut -d: -f1)

  sed -i "${insert_line}a\\${entry}" regtest/aports-html.sh
}

proc download-report(epoch) {
  rename-editing-epoch "$epoch"

  regtest/aports-html.sh sync-old-wwz
}

proc prepare-new-report(original_epoch, new_epoch, use_main) {
  regtest/aports-html.sh extract-old-wwz $new_epoch

  # add-report-entry $original_epoch $new_epoch $use_main
}

proc generate-new-report(new_epoch, use_main) {
  # assuming runs from main are full runs and from community partial
  # this might break, should probably find a better way to do this
  # Maybe check contents of _tmp/aports-report/$original_epoch?
  if (use_main === 'true') {
    regtest/aports-html.sh write-all-reports "_tmp/aports-report/$new_epoch"
  } else {
    regtest/aports-html.sh write-disagree-reports "_tmp/aports-report/$new_epoch"
  }
}

proc deploy-new-report(new_epoch) {
  regtest/aports-html.sh make-wwz "_tmp/aports-report/$new_epoch"
  regtest/aports-html.sh deploy-wwz-op "_tmp/aports-report/$new_epoch.wwz"
}

proc update-latest() {
  ### Create a new report based on the most recent published report
  ### Create the new report using a newer `causes.awk` file
  ### Does the following steps:
  ### 0. Determine latest report
  ### 1. Fetch latest published report
  ### 2. Add entry of new report to published.html
  ### 3. Generate report using new causes.awk
  ### 4. Upload new report
  ###
  ### Current limitations:
  ### Can run only once per day, otherwise $new_epoch already exists
  ### Assumes community runs are partial runs, and main runs are full.
  ###    If this is not true the script breaks
  stdout_to_stderr
  set -x

  var original_epoch = ENV.REGTEST_CAUSES_BASE_REPORT
  var kind = ENV.REGTEST_CAUSES_KIND
  
  var use_main = useMainReports(kind)
  if (use_main === false and useCommunityReports(kind) === false) {
    echo "kind should be main or community, got: $kind"
    exit 1
  }

  var new_epoch = calculateNewEpoch(use_main)

  echo "Generating new report with epoch $new_epoch based on $original_epoch for $kind"

  download-report $original_epoch
  
  prepare-new-report $original_epoch $new_epoch $use_main

  generate-new-report $new_epoch $use_main

  deploy-new-report $new_epoch

  restore_stdout

  echo "New report available at: https://op.oils.pub/aports-build/$new_epoch.wwz/_tmp/aports-report/$new_epoch/diff_merged.html"
}

runproc @ARGV
