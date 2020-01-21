#!/bin/bash
#
# Usage:
#   ./release-version.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # html-head

# NOTE: Left to right evaluation would be nice on this!
#
# Rewrite in oil:
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
    with #<a href="/blog/tags.html?tag=oil-release#oil-release">oil-release</a>.
    </p>
  </body>
</html>  
EOF
}

write-no-announcement() {
  no-announcement > _release/VERSION/announcement.html
}

readonly SITE_DEPLOY_DIR='../oilshell.org__deploy'

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
  write-no-announcement
}

blog-redirect() {
  html-redirect 'making-plans.html' > $SITE_DEPLOY_DIR/blog/2020/01/11.html
}


"$@"
