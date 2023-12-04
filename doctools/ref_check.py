#!/usr/bin/env python2
"""
ref_check.py: Check Links
"""
from __future__ import print_function

import collections
import json
from pprint import pprint
import sys

from doctools.util import log


def PrintTree(node, f, indent=0):
  """
  Print DocNode tree in make_help.py
  """
  if node.attrs:
    a_str = ', '.join('%s=%s' % pair for pair in node.attrs)
    a_str = '(%s)' % a_str
  else:
    a_str = ''

  print('%s%s %s' % (indent * '  ', node.name, a_str), file=f)
  for ch in node.children:
    PrintTree(ch, f, indent+1)


def Check(all_toc_nodes, chap_tree):
  """
  Args:
    all_toc_nodes: Structure of doc/ref/toc-*.md
    chap_tree: Structure of chap-*.html
  """

  #pprint(all_toc_nodes)

  #sections = []
  all_topics = []

  link_from = set()
  link_to = set()

  section_check = collections.defaultdict(list)
  toc_topic_check = collections.defaultdict(list)

  for toc_node in all_toc_nodes:
    toc = toc_node['toc']
    print(toc)
    for box_node in toc_node['boxes']:
      to_chap = box_node['to_chap']
      print('  %s' % to_chap)
      for line_info in box_node['lines']:
        section = line_info['section']
        topics = line_info['topics']
        for topic in topics:
          toc_topic_check[topic].append(toc)

          chap_filename = 'chap-%s.html' % to_chap
          link_from.add((chap_filename, topic))

        all_topics.extend(topics)

        #print('    %s: %s' % (section or '?', ' '.join(topics)))

  log('')

  log('Topics in TOC: %d', len(all_topics))
  log('Unique topics in TOC: %d', len(set(all_topics)))
  log('')

  log('Duplicate topics in TOC:')
  log('')
  for topic in sorted(toc_topic_check):
    toc_list = toc_topic_check[topic]
    if len(toc_list) > 1:
      log('%20s: %s', topic, ' '.join(toc_list))
  log('')

  log('%d in link_from set: %s', len(link_from), sorted(link_from)[:10])
  log('')

  if 0:
    PrintTree(chap_tree, sys.stdout)

  num_chapters = 0
  num_sections = 0
  num_topics = 0

  chap_topics = collections.defaultdict(list)  # topic_id -> list of chapters

  for chap in chap_tree.children:
    num_chapters += 1

    for section in chap.children:
      num_sections += 1

      for topic in section.children:
        num_topics += 1

        values = [v for k, v in topic.attrs if k == 'id']
        if len(values) == 1:
          topic_id = values[0]
        else:
          topic_id = topic.name

        chap_topics[topic_id].append(chap.name)
        link_to.add((chap.name, topic.name))

  log('%d in link_to set: %s', len(link_to), sorted(link_to)[:10])
  log('')

  num_sections = sum(len(child.children) for child in chap_tree.children)
  num_sections = sum(len(child.children) for child in chap_tree.children)
  log('Chapter stats')
  log('  num chapters = %d', num_chapters)
  log('  num_sections = %d', num_sections)
  log('  num_topics = %d', num_topics)

  chap_topic_set = set(chap_topics)
  log('  num unique topics = %d', len(chap_topic_set))
  log('')

  index_topic_set = set(toc_topic_check)

  assert 'j8-escape' in index_topic_set
  assert 'j8-escape' in chap_topic_set

  broken = link_from - link_to
  log('%d Broken Links:', len(broken))
  for pair in sorted(broken):
    log('  %s', pair)
  log('')

  orphaned = link_to - link_from
  log('%d Orphaned Topics:', len(orphaned))
  for pair in sorted(orphaned):
    log('  %s', pair)
  log('')


  if 0:
    not_linked_to = chap_topic_set - index_topic_set
    log('')
    log('%d topics not linked to:', len(not_linked_to))
    for topic_id in not_linked_to:
      log('  %s in %s', topic_id, chap_topics[topic_id])

  log('')
  log('Topics in multiple chapters:')
  for topic_id, chaps in chap_topics.iteritems():
    if len(chaps) > 1:
      print('%s %s' % (topic_id, chaps))


# vim: sw=2
