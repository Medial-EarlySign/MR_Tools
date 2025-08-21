## Documentation of Statins Effect

### Technical Overview

To accurately assess the effect of statins, precise and cautious definitions are crucial. Small mistakes or omissions can lead to misleading results, such as falsely concluding that statins are harmful — similar to how diet soda is often misinterpreted as causing weight gain due to correlation rather than causation.

### High-Level Methodology

1. **MI Registry Construction**  
   We created a registry of **first** myocardial infarction (MI) events. Patient follow-up periods were inferred based on LDL and cholesterol test records.

2. **Sampling Framework**  
   For each patient, we randomly sampled one date per year within a specific range (e.g., 2007–2015). These dates serve as potential "index dates" for inclusion in the experiment.

3. **Statin Identification**  
   Statins were identified using ATC code **C10**. Our infrastructure captures all medications categorized under this group.

4. **Cohort Filtering**  
   We excluded patients who had taken statins prior to the index date. This ensures a "clean" baseline cohort - all patients are initially untreated, and only some begin statin therapy at the index date.

5. **Outcome Time Horizon**  
   Follow-up periods were set between **1 to 5 years** to allow time for statins to demonstrate clinical effect.

6. **Sample Deduplication**  
   We retained only **one random sample per patient per outcome**, to avoid overrepresentation of individuals with multiple samples.

7. **Treatment Definition**  
   - **Treated group**: Patients with **50%–100%** adherence to statin prescriptions during follow-up (inclusive).
   - **Untreated group**: Patients with **0%–5%** adherence (inclusive).
   - Patients with **5%–50%** adherence were excluded due to ambiguity in treatment status.

### Propensity Score Matching Variables

Matching was performed using the following covariates:

- **Demographics**: Age, Sex  
- **Comorbidities**: Diabetes, Smoking Status  
- **Recent Lab Values** (most recent before index date):  
  - Blood pressure  
  - Lipid panel: Cholesterol, LDL, etc.  
  - Hemoglobin, Hematocrit, RBC, RDW  
  - Glucose, HbA1C  
  - BMI  
  - Creatinine, Urea  
  - Liver enzymes: ALT, AST, ALKP  
  - eGFR

- **Drug History (last 3 years)**: Use of medications in the following ATC classes:  
  `ATC_C08C, ATC_C07B, ATC_C07C, ATC_C07D, ATC_C07F, ATC_C07AG, ATC_C09B, ATC_C09D, ATC_C02DA01`

### Results

The methodology produced strong and consistent results. We observed a **40–50% reduction** in the probability of myocardial infarction (MI) among patients treated with statins.

- **Without propensity score matching**, the analysis misleadingly showed a **higher MI risk** for statin users - an example of confounding and selection bias.
- After matching, the **true treatment effect** of statins became evident.

We further analyzed the effect based on **LDL reduction**:

- The treatment effect was **only present when LDL levels actually decreased**, which aligns with the expected biological mechanism.
- Interestingly, even patients **not on statins** who experienced a natural or unrelated **LDL reduction** showed a similar risk reduction (or problem in drugs registration).
- This suggests that the **primary driver of MI risk reduction is the lowering of LDL levels**, whether through statins or other means.
