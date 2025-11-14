-- Disagreements

select '<table id="summary-table">';

select
  printf(
    '<tr> <td>Notable Disagreements:</td> <td class="num"><b>%d</b></td> </tr>',
    count(*)
  )
from notable_disagree;
select
  printf(
    '<tr> <td>Elapsed Hours:</td> <td class="num"><b>%.1f</b></td> </tr>',
    sum(elapsed_minutes) / 60
  )
from metrics;

select '</table>';
