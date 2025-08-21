SELECT status_name, 
sum(cnt) as cnt
	FROM etl.thin_stats 
    where content in ('TOTAL')
    group by status_name
 order by cnt desc
 
 
 select t.*, bad_sum / (bad_sum + good_sum) as rtaio  from
 (select t.*, max( (case when status_name <> 'read' and status_name <> 'wrote_numeric' and status_name <> 'wrote_non_numeric'
                 then cnt 
                 else 0 end) )  over (partition by pracId) as max_cnt ,
                 sum(case when status_name <> 'read' and status_name <> 'wrote_numeric' and status_name <> 'wrote_non_numeric'
                 then cnt 
                 else 0 end)   over (partition by pracId) as bad_sum, 
                  sum(case when not(status_name <> 'read' and status_name <> 'wrote_numeric' and status_name <> 'wrote_non_numeric')
                 then cnt 
                 else 0 end)   over (partition by pracId) as good_sum
                 from
 (SELECT pracId, status_name,
sum(cnt) as cnt
	FROM etl.thin_stats 
    where content  in ('TOTAL')
  and status_name <> 'read'
    group by pracId, status_name) t
 ) t
 order by bad_sum / (bad_sum + good_sum) desc, pracid, cnt desc
