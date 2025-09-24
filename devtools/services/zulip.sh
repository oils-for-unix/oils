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

# private AUTH
. zulip-env.sh

my-curl() {
  # --get affects -d
  curl \
    --silent --show-error --get \
    "$@"
}

messages-in-stream() {
  local bot_email=${1:-$ZULIP_EMAIL}
  local bot_api_key=${2:-$ZULIP_KEY}
  local stream=${3:-'blog-ideas'}
  local apply_markdown=${4:-false}  # or 'true'

  local narrow='[{"operand": "'$stream'", "operator": "stream"}]'

  # copied from example at https://zulip.com/api/get-messages 
  my-curl \
    -u "$bot_email:$bot_api_key" \
    -d 'anchor=newest' \
    -d 'num_before=3000' \
    -d 'num_after=0' \
    -d "apply_markdown=$apply_markdown" \
    --data-urlencode narrow="$narrow" \
    https://oilshell.zulipchat.com/api/v1/messages 

    # doesn't work
    # --data-urlencode narrow='[{"operand": "0.8.4 Release Notes", "operator": "topic"}]' \
}

print-thread() {
  # Get these from Zulip web interface
  local bot_email=$1
  local bot_api_key=$2
  local stream=${3:-'oil-dev'}
  local subject=${4:-'Test thread'}
  local apply_markdown=${5:-false}  # or 'true'

  # https://stackoverflow.com/questions/28164849/using-jq-to-parse-and-display-multiple-fields-in-a-json-serially/31791436

  # JQ query
  # - narrow to messages array
  # - create record with content and subject field
  # - select records where subject is "needle" var
  # - print the content.  -r prints it raw.

  messages-in-stream "$bot_email" "$bot_api_key" "$stream" "$apply_markdown" | \
    jq --arg subject "$subject" -r \
    '.messages[] | { content: .content, subject: .subject } |
      select( .subject == $subject ) | (.content + "\n\n")'
}

print-both() {
  local prefix=${1:-_tmp/zulip/sept}
  mkdir -p "$(dirname $prefix)"

  local stream='blog-ideas'
  local subject='Oils September Status Update'

  print-thread $ZULIP_EMAIL $ZULIP_KEY "$stream" "$subject" false | tee $prefix.md
  print-thread $ZULIP_EMAIL $ZULIP_KEY "$stream" "$subject" true | tee $prefix.html

  ls -l $prefix*
}

to-html() {
  local prefix=${1:-_tmp/zulip/sept}

  doctools/cmark.sh cmark-py < $prefix.md > $prefix.cmark.html
  ls -l $prefix*
}

common-mark-prefix() {
  local date_str=$(date +'%Y/%m/%d')
  
  echo "\
---
title: Post created on $date_str
date: $date_str
css_file: blog-bundle-v7.css
body_css_class: width35
default_highlighter: oils-sh
comments_url: TODO
published: no
---

<div id="toc">
</div>

## Heading
"
}

to-common-mark() {
  local prefix=${1:-_tmp/zulip/sept}

  local dest=../oils.pub/blog/2025/09/_sept.md
  { common-mark-prefix
    cat $prefix.md | devtools/services/zulip.py 
  } > $dest
  echo "Wrote $dest"
}

#
# These weren't needed
#

topics() {
  local bot_email=$1
  local bot_api_key=$2

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
