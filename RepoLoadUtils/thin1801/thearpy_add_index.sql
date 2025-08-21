---DROP INDEX IF EXISTS therapy_dosecode_idx;
---CREATE INDEX therapy_dosecode_idx
  ---ON public.therapy (doscode) TABLESPACE  pg_default;
  
---DROP INDEX IF EXISTS public.therapy_patid_idx;
---CREATE INDEX public.therapy_patid_idx
---  ON public.therapy (patid) TABLESPACE  pg_default;
  
--- DROP INDEX IF EXISTS public.therapy_drugcode_idx;
--- CREATE INDEX public.therapy_drugcode_idx
---  ON public.therapy (drugcode) TABLESPACE  pg_default;

---DROP INDEX IF EXISTS public.therapy_prscqty_idx;
---CREATE INDEX public.therapy_prscqty_idx
--  ON public.therapy (prscqty) TABLESPACE  pg_default;  
  
--- DROP INDEX IF EXISTS public.therapy_prscdays_idx;
---CREATE INDEX public.therapy_prscdays_idx
---  ON public.therapy (prscdays) TABLESPACE  pg_default;
  
---DROP INDEX IF EXISTS public.therapy_prsctype_idx;
---CREATE INDEX public.therapy_prsctype_idx
  ---ON public.therapy (prsctype) TABLESPACE  pg_default;

---DROP INDEX IF EXISTS public.therapy_packsize_idx;
CREATE INDEX therapy_packsize_idx
  ON public.therapy (packsize) TABLESPACE  pg_default;
 
---DROP INDEX IF EXISTS public.therapy_dosgval_idx;
CREATE INDEX therapy_dosgval_idx
  ON public.therapy (dosgval) TABLESPACE  pg_default;
