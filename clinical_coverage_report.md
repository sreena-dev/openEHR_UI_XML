# Clinical Event Coverage Analysis

Based on a scan of the ADL (Archetype Definition Language) files present in your workspace, the system is equipped to handle an extraordinarily wide variety of clinical events and data points. 

Here is a breakdown of the coverage capabilities, categorized by the modular components of openEHR:

## 1. High-Level Encounters & Documents (Compositions)
There are **32 Composition archetypes** that define the structure of main clinical documents. These represent the "wrappers" or the forms themselves:
*   **General Clinical:** `encounter`, `care_plan`, `progress_note`, `event_summary`, `health_summary`, `transfer_summary`
*   **History & Risk:** `family_history`, `lifestyle_factors`, `social_summary`, `obstetric_history`
*   **Medication & Action:** `medication_list`, `prescription`, `vaccination_list`, `adverse_reaction_list`
*   **Reporting:** `report`, `report-clinical_investigation`, `report-procedure`, `report-result`, `report-post_mortem`
*   **Specialized:** `disease_surveillance`, `pregnancy_summary`, `health_certificate`

## 2. Clinical Sections (Document Groupings)
There are **31 Section archetypes** used to neatly group related data within those compositions:
*   **Patient Context:** `patients_background`, `patients_admittance`, `family_history`, `lifestyle_risk_factors`
*   **Clinical Status:** `vital_signs`, `problem_list`, `immunisation_list`, `adverse_reaction_list`
*   **Process/Workflow:** `soap` (Subjective, Objective, Assessment, Plan), `referral_details`, `clinical_decision`, `next_step_planning`
*   **Diagnostics/Results:** `lab_test_report`, `diagnostic_reports`, `diagnostic_model`
*   **Specialized (Ophthalmology explicitly visible):** `eye_fundus_acquisition`, `intraocular_injection`, `intraocular_pressure_study`, `visual_acuity_study`

## 3. Specific Clinical Data Points (Clusters & Entries)
The overwhelming majority of the detail lies in the **365 Cluster archetypes** (reusable data blocks) and numerous Entry archetypes (Observations, Evaluations, Instructions, Actions).

### Major Domains Covered:

*   **Physical Examinations (Extensive!):**
    *   General: `abdomen`, `chest`, `heart`, `lung`, `skin`, `nervous_system`, `respiratory_system`, `cardiovascular_system`
    *   Specific/Local: `breasts`, `face`, `neck`, `thyroid`, `lymph_node`
    *   ENT/Dental: `ear`, `nose`, `mouth`, `throat`, `teeth`, `tongue`, `tympanic_membrane`
    *   Musculoskeletal: `upper_limb`, `lower_limb`, `spine`, `joint`, `muscle_power`, `gait`, `tenderness`
    *   Pelvic/Uro: `anus`, `rectum`, `prostate`, `cervix`, `vagina`, `uterus`, `scrotum`
*   **Ophthalmology (Deeply Specialized):**
    *   Examinations: `eye`, `pupil`, `cornea`, `lens`, `retina`, `optic_disc`, `macula`
    *   Measurements: `corneal_thickness`, `intraocular_pressure`, `visual_field`, `refraction_details`
    *   Pathology/Therapy: `glaucoma_classification`, `diabetic_retinopathy`, `photocoagulation`, `intravitreal_injection`
*   **Genomics & Pathology (Extremely Detailed):**
    *   Genomics: `variant_result`, `copy_number_variant`, `substitution_variant`, `gene`, `pharmacogenetic_test`
    *   Pathology / Oncology: `tumour_invasion`, `gleason_score`, `tnm_staging`, `lymph_node_metastases`, `resection_margins`
    *   Microscopy specifically for: `melanoma`, `breast_carcinoma`, `prostate_carcinoma`, `colorectal_carcinoma`, `lymphoma`
*   **Imaging & Diagnostics:**
    *   `imaging_exam` (broken down into dozens of specific organs: liver, heart, pelvis, foetus, sacrum, etc.)
    *   `laboratory_test_panel`, `blood_cell_count`, `microbiology_culture`
*   **Vitals & Lifestyle:**
    *   `blood_pressure`, `heart_rate`, `respiration`, `temperature`
    *   `alcohol_consumption`, `smoking`, `physical_activity`, `dietary_nutrients`
*   **Medication & Devices:**
    *   `medication_order`, `dosage`, `administration`
    *   `device_details`, `implantable_devices` (e.g., `hip_arthroplasty_component`)

## What Does This Mean for You?

You have the building blocks (Archetypes) to capture almost **any standard clinical event** in general practice, nursing, emergency care, and several highly specialized fields (especially Ophthalmology, Genomics, and Oncology).

**To explicitly create a form for the UI:**
You (or your template designer) use an openEHR tool (like Archetype Designer) to combine these Archetypes into a **Template (.opt file)**. 
For example, you could combine:
`Composition(encounter) -> Section(vitals) -> Observation(blood_pressure) + Observation(heart_rate)`

You currently have templates loaded into EHRbase (like the `blood_pressure` template we saw earlier), but the *potential* variety you can support is virtually boundless given this vast archetype repository.
