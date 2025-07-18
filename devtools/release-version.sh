#!/usr/bin/env bash
#
# Usage:
#   ./release-version.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # html-head

# NOTE: Left to right evaluation would be nice on this!
#
# Rewrite in YSH:
# 
# sys.stdin.read() | sub( / "\x00" { any* } "\x01" /, html_escape) | write
escape-segments() {
  python -c '
import cgi, re, sys

print re.sub(
  r"\x00(.*)\x01", 
  lambda match: cgi.escape(match.group(1)),
  sys.stdin.read())
'
}

# TODO: It would be nice to have a column of bugs fixed / addressed!

_git-changelog-body() {
  local prev_branch=$1
  local cur_branch=$2
  shift 2

  # - a trick for HTML escaping (avoid XSS): surround %s with unlikely bytes,
  #   \x00 and \x01.  Then pipe Python to escape.
  # --reverse makes it go in forward chronlogical order.

  # %x00 generates the byte \x00
  local format='<tr>
    <td><a class="checksum"
           href="https://github.com/oilshell/oil/commit/%H">%h</a>
    </td>
    <td class="date">%ad</td>
    <td>%x00%an%x01</td>
    <td class="subject">%x00%s%x01</td>
  </tr>'
  git log \
    $prev_branch..$cur_branch \
    --reverse \
    --pretty="format:$format" \
    --date=short \
    "$@" \
  | escape-segments
}

_git-changelog-header() {
  local prev_branch=$1
  local cur_branch=$2

  html-head --title "Commits Between Branches $prev_branch and $cur_branch" \
    'web/base.css' 'web/changelog.css'

  cat <<EOF
  <body class="width60">
    <h3>Commits Between Branches <code>$prev_branch</code> and
       <code>$cur_branch</code></h3>
    <table>
      <colgroup>
        <col>
        <col>
        <col>
        <!-- prevent long commits from causing wrapping in other cells -->
        <col style="width: 40em">
      </colgroup>
EOF
# Doesn't seem necessary now.
#     <thead>
#        <tr>
#          <td>Commit</td>
#          <td>Date</td>
#          <td>Description</td>
#        </tr>
#      </thead>
}

_git-changelog() {
  _git-changelog-header "$@"
  _git-changelog-body "$@"
  cat <<EOF
    </table>
  </body>
</html>
EOF
}

git-changelog-0.1() {
  local version='0.1.0'
  _git-changelog release/0.0.0 release/0.1.0 \
    > ../oilshell.org__deploy/release/$version/changelog.html
}

git-changelog-0.2.alpha1() {
  _git-changelog release/0.1.0 release/0.2.alpha1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.2.0() {
  _git-changelog release/0.1.0 release/0.2.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.3.alpha1() {
  _git-changelog release/0.2.0 release/0.3.alpha1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.3.0() {
  _git-changelog release/0.2.0 release/0.3.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.4.0() {
  _git-changelog release/0.3.0 release/0.4.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.5.alpha1() {
  _git-changelog release/0.4.0 release/0.5.alpha1 \
    > _release/VERSION/changelog.html
}

# Alpha release logs are relative to last minor release
git-changelog-0.5.alpha2() {
  _git-changelog release/0.5.alpha1 release/0.5.alpha2 \
    > _release/VERSION/changelog.html
}

git-changelog-0.5.alpha3() {
  _git-changelog release/0.5.alpha2 release/0.5.alpha3 \
    > _release/VERSION/changelog.html
}

# Hm if you're not releasing on the same machine as the previous release, the
# branch needs origin/ on the front?  Is this the best way to do it?
# NOTE: 'git branch -a' shows all branches.

git-changelog-0.5.0() {
  # NOTE: release/0.5 branch should be sync'd up with master squashes.
  _git-changelog origin/release/0.5.alpha3 release/0.5.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre1() {
  _git-changelog origin/release/0.5.0 release/0.6.pre1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre2() {
  _git-changelog origin/release/0.6.pre1 release/0.6.pre2 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre3() {
  _git-changelog origin/release/0.6.pre2 release/0.6.pre3 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre4() {
  _git-changelog origin/release/0.6.pre3 release/0.6.pre4 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre5() {
  _git-changelog origin/release/0.6.pre4 release/0.6.pre5 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre6() {
  _git-changelog origin/release/0.6.pre5 release/0.6.pre6 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre7() {
  _git-changelog origin/release/0.6.pre6 release/0.6.pre7 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre8() {
  _git-changelog origin/release/0.6.pre7 release/0.6.pre8 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre9() {
  _git-changelog origin/release/0.6.pre8 release/0.6.pre9 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre10() {
  _git-changelog origin/release/0.6.pre9 release/0.6.pre10 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre11() {
  _git-changelog origin/release/0.6.pre10 release/0.6.pre11 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre12() {
  _git-changelog origin/release/0.6.pre11 release/0.6.pre12 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre13() {
  _git-changelog origin/release/0.6.pre12 release/0.6.pre13 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre14() {
  _git-changelog origin/release/0.6.pre13 release/0.6.pre14 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre15() {
  _git-changelog origin/release/0.6.pre14 release/0.6.pre15 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre16() {
  _git-changelog origin/release/0.6.pre15 release/0.6.pre16 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre17() {
  _git-changelog origin/release/0.6.pre16 release/0.6.pre17 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre18() {
  _git-changelog origin/release/0.6.pre17 release/0.6.pre18 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre19() {
  _git-changelog origin/release/0.6.pre18 release/0.6.pre19 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre20() {
  _git-changelog origin/release/0.6.pre19 release/0.6.pre20 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre21() {
  _git-changelog origin/release/0.6.pre20 release/0.6.pre21 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre22() {
  _git-changelog origin/release/0.6.pre21 release/0.6.pre22 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.pre23() {
  _git-changelog origin/release/0.6.pre22 release/0.6.pre23 \
    > _release/VERSION/changelog.html
}

git-changelog-0.6.0() {
  _git-changelog origin/release/0.6.pre23 release/0.6.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre1() {
  _git-changelog origin/release/0.6.0 release/0.7.pre1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre2() {
  _git-changelog origin/release/0.7.pre1 release/0.7.pre2 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre3() {
  _git-changelog origin/release/0.7.pre2 release/0.7.pre3 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre4() {
  _git-changelog origin/release/0.7.pre3 release/0.7.pre4 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre5() {
  _git-changelog origin/release/0.7.pre4 release/0.7.pre5 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre6() {
  _git-changelog origin/release/0.7.pre5 release/0.7.pre6 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre7() {
  _git-changelog origin/release/0.7.pre6 release/0.7.pre7 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre8() {
  _git-changelog origin/release/0.7.pre7 release/0.7.pre8 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre9() {
  _git-changelog origin/release/0.7.pre8 release/0.7.pre9 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre10() {
  _git-changelog origin/release/0.7.pre9 release/0.7.pre10 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.pre11() {
  _git-changelog origin/release/0.7.pre10 release/0.7.pre11 \
    > _release/VERSION/changelog.html
}

git-changelog-0.7.0() {
  _git-changelog origin/release/0.7.pre11 release/0.7.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre1() {
  _git-changelog origin/release/0.7.0 release/0.8.pre1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre2() {
  _git-changelog origin/release/0.8.pre1 release/0.8.pre2 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre3() {
  _git-changelog origin/release/0.8.pre2 release/0.8.pre3 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre4() {
  _git-changelog origin/release/0.8.pre3 release/0.8.pre4 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre5() {
  _git-changelog origin/release/0.8.pre4 release/0.8.pre5 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre6() {
  _git-changelog origin/release/0.8.pre5 release/0.8.pre6 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre7() {
  _git-changelog origin/release/0.8.pre6 release/0.8.pre7 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre8() {
  _git-changelog origin/release/0.8.pre7 release/0.8.pre8 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre9() {
  _git-changelog origin/release/0.8.pre8 release/0.8.pre9 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre10() {
  _git-changelog origin/release/0.8.pre9 release/0.8.pre10 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.pre11() {
  _git-changelog origin/release/0.8.pre10 release/0.8.pre11 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.0() {
  _git-changelog origin/release/0.8.pre11 release/0.8.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.1() {
  _git-changelog origin/release/0.8.0 release/0.8.1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.2() {
  _git-changelog origin/release/0.8.1 release/0.8.2 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.3() {
  _git-changelog origin/release/0.8.2 release/0.8.3 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.4() {
  _git-changelog origin/release/0.8.3 release/0.8.4 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.5() {
  _git-changelog origin/release/0.8.4 release/0.8.5 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.6() {
  _git-changelog origin/release/0.8.5 release/0.8.6 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.7() {
  _git-changelog origin/release/0.8.6 release/0.8.7 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.8() {
  _git-changelog origin/release/0.8.7 release/0.8.8 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.9() {
  _git-changelog origin/release/0.8.8 release/0.8.9 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.10() {
  _git-changelog origin/release/0.8.9 release/0.8.10 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.11() {
  _git-changelog origin/release/0.8.10 release/0.8.11 \
    > _release/VERSION/changelog.html
}

git-changelog-0.8.12() {
  _git-changelog origin/release/0.8.11 release/0.8.12 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.0() {
  _git-changelog origin/release/0.8.12 release/0.9.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.1() {
  _git-changelog origin/release/0.9.0 release/0.9.1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.3() {
  _git-changelog origin/release/0.9.2 release/0.9.3 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.4() {
  _git-changelog origin/release/0.9.3 release/0.9.4 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.5() {
  _git-changelog origin/release/0.9.4 release/0.9.5 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.6() {
  _git-changelog origin/release/0.9.5 release/0.9.6 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.7() {
  _git-changelog origin/release/0.9.6 release/0.9.7 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.8() {
  _git-changelog origin/release/0.9.7 release/0.9.8 \
    > _release/VERSION/changelog.html
}

git-changelog-0.9.9() {
  _git-changelog origin/release/0.9.8 release/0.9.9 \
    > _release/VERSION/changelog.html
}

git-changelog-0.10.0() {
  _git-changelog origin/release/0.9.9 release/0.10.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.10.1() {
  _git-changelog origin/release/0.10.0 release/0.10.1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.11.0() {
  _git-changelog origin/release/0.10.1 release/0.11.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.0() {
  _git-changelog origin/release/0.11.0 release/0.12.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.3() {
  _git-changelog origin/release/0.12.0 release/0.12.3 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.4() {
  _git-changelog origin/release/0.12.3 release/0.12.4 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.5() {
  _git-changelog origin/release/0.12.4 release/0.12.5 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.6() {
  _git-changelog origin/release/0.12.5 release/0.12.6 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.7() {
  _git-changelog origin/release/0.12.6 release/0.12.7 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.8() {
  _git-changelog origin/release/0.12.7 release/0.12.8 \
    > _release/VERSION/changelog.html
}

git-changelog-0.12.9() {
  _git-changelog origin/release/0.12.8 release/0.12.9 \
    > _release/VERSION/changelog.html
}

git-changelog-0.13.0() {
  _git-changelog origin/release/0.12.9 release/0.13.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.13.1() {
  _git-changelog origin/release/0.13.0 release/0.13.1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.14.0() {
  _git-changelog origin/release/0.13.1 release/0.14.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.14.1() {
  _git-changelog origin/release/0.14.0 release/0.14.1 \
    > _release/VERSION/changelog.html
}

git-changelog-0.14.2() {
  _git-changelog origin/release/0.14.1 release/0.14.2 \
    > _release/VERSION/changelog.html
}

git-changelog-0.15.0() {
  _git-changelog origin/release/0.14.2 release/0.15.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.16.0() {
  _git-changelog origin/release/0.15.0 release/0.16.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.17.0() {
  _git-changelog origin/release/0.16.0 release/0.17.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.18.0() {
  _git-changelog origin/release/0.17.0 release/0.18.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.19.0() {
  _git-changelog origin/release/0.18.0 release/0.19.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.20.0() {
  _git-changelog origin/release/0.19.0 release/0.20.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.21.0() {
  _git-changelog origin/release/0.20.0 release/0.21.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.22.0() {
  _git-changelog origin/release/0.21.0 release/0.22.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.23.0() {
  _git-changelog origin/release/0.22.0 release/0.23.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.24.0() {
  _git-changelog origin/release/0.23.0 release/0.24.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.25.0() {
  _git-changelog origin/release/0.24.0 release/0.25.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.26.0() {
  _git-changelog origin/release/0.25.0 release/0.26.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.27.0() {
  _git-changelog origin/release/0.26.0 release/0.27.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.28.0() {
  _git-changelog origin/release/0.27.0 release/0.28.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.29.0() {
  _git-changelog origin/release/0.28.0 release/0.29.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.30.0() {
  _git-changelog origin/release/0.29.0 release/0.30.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.31.0() {
  _git-changelog origin/release/0.30.0 release/0.31.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.32.0() {
  _git-changelog origin/release/0.31.0 release/0.32.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.33.0() {
  _git-changelog origin/release/0.32.0 release/0.33.0 \
    > _release/VERSION/changelog.html
}

git-changelog-0.34.0() {
  _git-changelog origin/release/0.33.0 release/0.34.0 \
    > _release/VERSION/changelog.html
}

# For announcement.html
html-redirect() {
  local url=$1
  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="refresh" content="0; url=$url" />
  </head>
  <body>
    <p>Redirect to<a href="$url">$url</a></p>
  </body>
</html>  
EOF
}

no-announcement() {
  html-head --title 'No announcement'
  cat <<EOF
  <body>
    <p>No announcement for this release.  Previous announcements are tagged
    with #<a href="/blog/tags.html?tag=oils-release#oils-release">oils-release</a>.
    </p>
  </body>
</html>  
EOF
}

write-no-announcement() {
  no-announcement > _release/VERSION/announcement.html
}

readonly SITE_DEPLOY_DIR='../../oilshell/oilshell.org__deploy'

announcement-0.0() {
  html-redirect '/blog/2017/07/23.html' \
    > ../oilshell.org__deploy/release/0.0.0/announcement.html
}

announcement-0.1() {
  local version='0.1.0'
  html-redirect '/blog/2017/09/09.html' \
    > ../oilshell.org__deploy/release/$version/announcement.html
}

announcement-0.2() {
  html-redirect '/blog/2017/11/10.html' > _release/VERSION/announcement.html
}

announcement-0.3() {
  html-redirect '/blog/2017/12/22.html' > _release/VERSION/announcement.html
  #no-announcement > _release/VERSION/announcement.html
}

announcement-0.4() {
  html-redirect '/blog/2018/02/03.html' > _release/VERSION/announcement.html
}

announcement-0.5.alpha3() {
  html-redirect '/blog/2018/04/30.html' > _release/VERSION/announcement.html
}

announcement-0.5() {
  html-redirect '/blog/2018/07/12.html' > _release/VERSION/announcement.html
}

announcement-0.6.pre1() {
  html-redirect '/blog/2018/08/15.html' > _release/VERSION/announcement.html
}

announcement-0.6.pre2() {
  html-redirect '/blog/2018/08/19.html' > _release/VERSION/announcement.html
}

announcement-0.6.pre3() {
  write-no-announcement
}

announcement-0.6.pre4() {
  write-no-announcement
}

announcement-0.6.pre5() {
  html-redirect '/blog/2018/10/11.html' > $SITE_DEPLOY_DIR/release/0.6.pre5/announcement.html
}

announcement-0.6.pre6() {
  no-announcement > $SITE_DEPLOY_DIR/release/0.6.pre6/announcement.html
}

announcement-0.6.pre7() {
  write-no-announcement
}

announcement-0.6.pre8() {
  html-redirect '/blog/2018/11/15.html' > $SITE_DEPLOY_DIR/release/0.6.pre8/announcement.html
}

announcement-0.6.pre9() {
  write-no-announcement
}

announcement-0.6.pre10() {
  write-no-announcement
}

announcement-0.6.pre11() {
  html-redirect '/blog/2018/12/16.html' > $SITE_DEPLOY_DIR/release/0.6.pre11/announcement.html
}

announcement-0.6.pre12() {
  html-redirect '/blog/2019/01/18.html' > $SITE_DEPLOY_DIR/release/0.6.pre12/announcement.html
}

announcement-0.6.pre13() {
  html-redirect '/blog/2019/02/05.html' > $SITE_DEPLOY_DIR/release/0.6.pre13/announcement.html
}

announcement-0.6.pre14() {
  html-redirect '/blog/2019/02/18.html' > $SITE_DEPLOY_DIR/release/0.6.pre14/announcement.html
}

announcement-0.6.pre15() {
  html-redirect '/blog/2019/02/18.html' > $SITE_DEPLOY_DIR/release/0.6.pre15/announcement.html
}

announcement-0.6.pre16-to-22() {
  for i in {16..22}; do
    html-redirect '/blog/2019/06/13.html' > $SITE_DEPLOY_DIR/release/0.6.pre$i/announcement.html
  done
}

announcement-0.6.pre23() {
  html-redirect '/blog/2019/07/19.html' > $SITE_DEPLOY_DIR/release/0.6.pre23/announcement.html
}

announcement-0.6.0() {
  html-redirect '/blog/2019/07/19.html' > $SITE_DEPLOY_DIR/release/0.6.0/announcement.html
}

announcement-0.7.pre1() {
  html-redirect '/blog/2019/07/19.html' > $SITE_DEPLOY_DIR/release/0.7.pre1/announcement.html
}

announcement-0.7.pre2() {
  write-no-announcement
}

announcement-0.7.pre3() {
  write-no-announcement
}

announcement-0.7.pre4() {
  write-no-announcement
}

announcement-0.7.pre5() {
  write-no-announcement
}

announcement-0.7.pre6() {
  html-redirect '/blog/2016/12/09.html' > $SITE_DEPLOY_DIR/release/0.7.pre6/announcement.html
}

announcement-0.7.pre7() {
  html-redirect '/blog/2019/12/09.html' > $SITE_DEPLOY_DIR/release/0.7.pre7/announcement.html
}

announcement-0.7.pre8() {
  html-redirect '/blog/2019/12/09.html' > $SITE_DEPLOY_DIR/release/0.7.pre8/announcement.html
}

announcement-0.7.pre9() {
  html-redirect '/blog/2019/12/09.html' > $SITE_DEPLOY_DIR/release/0.7.pre9/announcement.html
}

announcement-0.7.pre10() {
  write-no-announcement
}

announcement-0.7.pre11() {
  write-no-announcement
}

announcement-0.7.0() {
  html-redirect '/blog/2020/02/recap.html' > $SITE_DEPLOY_DIR/release/0.7.0/announcement.html
}

announcement-0.8.pre1() {
  html-redirect '/blog/2020/02/recap.html' > $SITE_DEPLOY_DIR/release/0.8.pre1/announcement.html
}

announcement-0.8.pre2() {
  html-redirect '/blog/2020/03/release-metrics.html' > $SITE_DEPLOY_DIR/release/0.8.pre2/announcement.html
}

announcement-0.8.pre3() {
  html-redirect '/blog/2020/03/release-0.8.pre3.html' > $SITE_DEPLOY_DIR/release/0.8.pre3/announcement.html
}

announcement-0.8.pre4() {
  html-redirect '/blog/2020/04/release-0.8.pre4.html' > $SITE_DEPLOY_DIR/release/0.8.pre4/announcement.html
}

announcement-0.8.pre5() {
  html-redirect '/blog/2020/05/translation-progress.html' > $SITE_DEPLOY_DIR/release/0.8.pre5/announcement.html
}

announcement-0.8.pre6() {
  html-redirect '/blog/2020/06/release-0.8.pre6.html' > $SITE_DEPLOY_DIR/release/0.8.pre6/announcement.html
}

announcement-0.8.pre7() {
  write-no-announcement
}

announcement-0.8.pre8() {
  write-no-announcement
}

announcement-0.8.pre9() {
  write-no-announcement
}

announcement-0.8.pre10() {
  write-no-announcement
}

announcement-0.8.pre11() {
  write-no-announcement
}

announcement-0.8.0() {
  write-no-announcement
}

announcement-0.8.1() {
  write-no-announcement
}

announcement-0.8.2() {
  write-no-announcement
}

announcement-0.8.3() {
  write-no-announcement
}

announcement-0.8.4() {
  write-no-announcement
}

announcement-0.8.5() {
  write-no-announcement
}

announcement-0.8.6() {
  write-no-announcement
}

announcement-0.8.7() {
  write-no-announcement
}

announcement-0.8.8() {
  write-no-announcement
}

announcement-0.8.9() {
  write-no-announcement
}

announcement-0.8.10() {
  write-no-announcement
}

announcement-0.8.11() {
  write-no-announcement
}

announcement-0.8.12() {
  write-no-announcement
}

announcement-0.9.0() {
  write-no-announcement
}

announcement-0.9.1() {
  write-no-announcement
}

announcement-0.9.3() {
  write-no-announcement
}

announcement-0.9.4() {
  write-no-announcement
}

announcement-0.9.5() {
  write-no-announcement
}

announcement-0.9.6() {
  write-no-announcement
}

announcement-0.9.7() {
  write-no-announcement
}

announcement-0.9.8() {
  write-no-announcement
}

announcement-0.9.9() {
  write-no-announcement
}

announcement-0.10.0() {
  write-no-announcement
}

announcement-0.10.1() {
  write-no-announcement
}

announcement-0.11.0() {
  write-no-announcement
}

announcement-0.12.0() {
  write-no-announcement
}

announcement-0.12.3() {
  write-no-announcement
}

announcement-0.12.4() {
  write-no-announcement
}

announcement-0.12.5() {
  write-no-announcement
}

announcement-0.12.6() {
  write-no-announcement
}

announcement-0.12.7() {
  html-redirect '/blog/2022/10/garbage-collector.html' > $SITE_DEPLOY_DIR/release/0.12.7/announcement.html
}

announcement-0.12.8() {
  write-no-announcement
}

announcement-0.12.9() {
  write-no-announcement
}

announcement-0.13.0() {
  write-no-announcement
}

announcement-0.13.1() {
  write-no-announcement
}

announcement-0.14.0() {
  write-no-announcement
}

announcement-0.14.1() {
  write-no-announcement
}

announcement-0.14.2() {
  html-redirect '/blog/2023/03/release-0.14.2.html' > $SITE_DEPLOY_DIR/release/0.14.2/announcement.html
}

announcement-0.15.0() {
  html-redirect '/blog/2023/05/release-0.15.0.html' > $SITE_DEPLOY_DIR/release/0.15.0/announcement.html
}

announcement-0.16.0() {
  html-redirect '/blog/2023/06/release-0.16.0.html' > $SITE_DEPLOY_DIR/release/0.16.0/announcement.html
}

announcement-0.17.0() {
  html-redirect '/blog/2023/08/release-0.17.0.html' > $SITE_DEPLOY_DIR/release/0.17.0/announcement.html
}

announcement-0.18.0() {
  html-redirect '/blog/2023/09/release-0.18.0.html' > $SITE_DEPLOY_DIR/release/0.18.0/announcement.html
}

announcement-0.19.0() {
  html-redirect '/blog/2024/01/release-0.19.0.html' > $SITE_DEPLOY_DIR/release/0.19.0/announcement.html
}

announcement-0.20.0() {
  html-redirect '/blog/2024/02/release-0.20.0.html' > $SITE_DEPLOY_DIR/release/0.20.0/announcement.html
}

announcement-0.21.0() {
  html-redirect '/blog/2024/03/release-0.21.0.html' > $SITE_DEPLOY_DIR/release/0.21.0/announcement.html
}

announcement-0.22.0() {
  html-redirect '/blog/2024/06/release-0.22.0.html' > $SITE_DEPLOY_DIR/release/0.22.0/announcement.html
}

announcement-0.23.0() {
  html-redirect '/blog/2024/11/release-0.23.0.html' > $SITE_DEPLOY_DIR/release/0.23.0/announcement.html
}

announcement-0.24.0() {
  html-redirect '/blog/2025/01/release-0.24.0.html' > $SITE_DEPLOY_DIR/release/0.24.0/announcement.html
}

announcement-0.25.0() {
  write-no-announcement
}

announcement-0.26.0() {
  write-no-announcement
}

announcement-0.27.0() {
  write-no-announcement
}

announcement-0.28.0() {
  write-no-announcement
}

announcement-0.29.0() {
  write-no-announcement
}

announcement-0.30.0() {
  write-no-announcement
}

announcement-0.31.0() {
  write-no-announcement
}

announcement-0.32.0() {
  write-no-announcement
}

announcement-0.33.0() {
  write-no-announcement
}

announcement-0.34.0() {
  write-no-announcement
}

blog-redirect() {
  html-redirect 'making-plans.html' > $SITE_DEPLOY_DIR/blog/2020/01/11.html
}

if test $(basename $0) = 'release-version.sh'; then
  "$@"
fi
