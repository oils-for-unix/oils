#!/usr/bin/env bash
#
# Usage:
#   devtools/services/zulip.sh <function name>
#
# https://oilshell.zulipchat.com -> Personal -> Bots for email and API key
#
# To get a thread, you have to get the messages in the stream, and the filter
# it with JQ.


set -o nounset
set -o pipefail
set -o errexit

my-curl() {
  curl \
    -s -S -X GET -G \
    "$@"
}

messages-in-stream() {
  local bot_email=$1
  local bot_api_key=$2

  # copied from example at https://zulip.com/api/get-messages 
  my-curl \
    -u "$bot_email:$bot_api_key" \
    -d 'anchor=newest' \
    -d 'num_before=50' \
    -d 'num_after=0' \
    -d 'apply_markdown=false' \
    --data-urlencode narrow='[{"operand": "oil-dev", "operator": "stream"}]' \
    https://oilshell.zulipchat.com/api/v1/messages 

    # doesn't work
    # --data-urlencode narrow='[{"operand": "0.8.4 Release Notes", "operator": "topic"}]' \
}

print-thread() {

  # JQ query
  # - narrow to messages array
  # - select content and subject field
  # - select only records where subject is a certain value
  # - then print the content.  -r prints it raw.

  # TODO: Make the subject an argument.  Maybe do fuzzy matching with JQ.

  # https://stackoverflow.com/questions/28164849/using-jq-to-parse-and-display-multiple-fields-in-a-json-serially/31791436

  messages-in-stream "$@" | jq -r \
    '.messages[] | { content: .content, subject: .subject } | select( .subject == "0.13.1 Release" ) | .content '
    #'{ content: .messages[].content, subject: .messages[].subject }'
    #'{ subject: .messages[].subject }'
}

#
# These weren't needed
#

topics() {
  local bot_email=$1
  local bot_api_key=$2

  # stream ID for #oil-discuss
  #local stream_id=121540

  # stream ID for #oil-dev.  You get the max ID
  local stream_id=121539

  my-curl \
    -u "$bot_email:$bot_api_key" \
    https://oilshell.zulipchat.com/api/v1/users/me/$stream_id/topics 
}

one-message() {
  local bot_email=$1
  local bot_api_key=$2

  # message ID from max_id of topics
  my-curl \
    -u "$bot_email:$bot_api_key" \
    https://oilshell.zulipchat.com/api/v1/messages/158997038
}

"$@"
