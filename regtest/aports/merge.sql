-- SQL invoked from regtest/aports-html.sh

update diff_merged
set
  baseline_HREF = printf("%s/%s", shard, baseline_HREF),
  osh_as_sh_HREF = printf("%s/%s", shard, osh_as_sh_HREF),
  error_grep_HREF = printf("%s/%s", shard, error_grep_HREF);
-- Useful queries to verify the result:
-- SELECT COUNT(*) as total_rows FROM diff_merged;
-- SELECT shard, COUNT(*) as row_count FROM diff_merged GROUP BY shard ORDER BY shard;
-- .schema diff_merged
