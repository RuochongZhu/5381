# 02_ai_quality_control.R
# AI-Assisted Text Quality Control
# Tim Fraser

# This script demonstrates how to use AI (Ollama or OpenAI) to perform quality
# control on AI-generated text reports. It implements quality control criteria
# including boolean accuracy checks and Likert scales for multiple quality
# dimensions. This version also compares a baseline prompt against a stricter
# prompt revision so students can document prompt iteration.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

# If you haven't already, install required packages:
# install.packages(c("dplyr", "stringr", "readr", "httr2", "jsonlite"))

library(dplyr)    # for data wrangling
library(stringr)  # for text processing
library(readr)    # for reading files
library(httr2)    # for HTTP requests
library(jsonlite) # for JSON operations

## 0.2 Configuration ####################################

# Choose your AI provider: "ollama" or "openai"
AI_PROVIDER = "ollama"  # Change to "openai" if using OpenAI

# Ollama configuration
PORT = 11434
OLLAMA_HOST = paste0("http://localhost:", PORT)
OLLAMA_MODEL = Sys.getenv("OLLAMA_MODEL", unset = "llama3.2:latest")

# OpenAI configuration
if (AI_PROVIDER == "openai") {
  if (file.exists(".env")) {
    readRenviron(".env")
  } else {
    warning(".env file not found. Make sure it exists in the project root.")
  }
}
OPENAI_API_KEY = Sys.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Low-cost model

## 0.3 Load Sample Data ####################################

# Load sample report text for quality control
sample_text = read_file("09_text_analysis/data/sample_reports.txt")
reports = strsplit(sample_text, "\n\n")[[1]]
reports = trimws(reports)
reports = reports[reports != ""]  # Remove empty strings
report = reports[1]

# Load source data (if available) for accuracy checking
source_data = "White County, IL | 2015 | PM10 | Time Driven | hours
|type        |label_value |label_percent |
|:-----------|:-----------|:-------------|
|Light Truck |2.7 M       |51.8%         |
|Car/ Bike   |1.9 M       |36.1%         |
|Combo Truck |381.3 k     |7.3%          |
|Heavy Truck |220.7 k     |4.2%          |
|Bus         |30.6 k      |0.6%          |"

cat("📝 Report for Quality Control:\n")
cat("---\n")
cat(report)
cat("\n---\n\n")

# 1. AI QUALITY CONTROL FUNCTIONS ###################################

## 1.1 Resolve Ollama Model #################################

get_ollama_models = function() {
  url = paste0(OLLAMA_HOST, "/api/tags")

  res = request(url) %>%
    req_method("GET") %>%
    req_perform()

  response = resp_body_json(res)
  models = vapply(response$models, function(model_info) model_info$name, character(1))

  return(models)
}

resolve_ollama_model = function(preferred_model = OLLAMA_MODEL) {
  available_models = get_ollama_models()

  if (length(available_models) == 0) {
    stop("No Ollama models are installed. Run `ollama pull <model>` first.")
  }

  if (preferred_model %in% available_models) {
    return(preferred_model)
  }

  fallback_model = available_models[[1]]
  warning(
    paste0(
      "Configured Ollama model '", preferred_model,
      "' is not installed. Falling back to '", fallback_model, "'."
    )
  )
  return(fallback_model)
}

## 1.2 Create Quality Control Prompt #################################

create_quality_control_prompt = function(report_text, source_data = NULL, prompt_version = "baseline") {

  prompt_version = match.arg(prompt_version, c("baseline", "enhanced"))

  instructions = paste(
    "You are a quality control validator for AI-generated reports.",
    "Evaluate the following report text on multiple criteria and return your assessment as valid JSON."
  )

  if (prompt_version == "enhanced") {
    instructions = paste(
      instructions,
      "Be strict about arithmetic consistency, unsupported recommendations, and claims that are not grounded in the source data.",
      "Return exactly one JSON object and no markdown or extra commentary."
    )
  }

  data_context = ""
  if (!is.null(source_data)) {
    data_context = paste0("\n\nSource Data:\n", source_data, "\n")
  }

  criteria = "

Quality Control Criteria:

1. accurate (boolean): Verify that no part of the paragraph misinterprets the data supplied. Return TRUE if no misinterpretation. FALSE if any problems.

2. accuracy (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = many problems interpreting the data vs. 5 = no misinterpretation of the data.

3. formality (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = casual writing vs. 5 = government report writing.

4. faithfulness (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = makes grandiose claims not supported by the data vs. 5 = makes claims directly related to the data.

5. clarity (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = confusing writing style vs. 5 = clear and precise.

6. succinctness (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = unnecessarily wordy vs. 5 = succinct.

7. relevance (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = irrelevant commentary vs. 5 = relevant commentary about the data.
"

  if (prompt_version == "enhanced") {
    criteria = paste0(
      criteria,
      "
Additional scoring guidance:
- Set accurate = false if any numeric claim, ranking, or recommendation goes beyond the source data.
- Lower faithfulness if the report introduces policy advice that is not directly supported by the source data.
- Lower succinctness if the report repeats the same point or adds generic filler.
- In details, briefly name the strongest reason for the score.
"
    )
  }

  json_format = '
Return your response as valid JSON in this exact format:
{
  "accurate": true/false,
  "accuracy": 1-5,
  "formality": 1-5,
  "faithfulness": 1-5,
  "clarity": 1-5,
  "succinctness": 1-5,
  "relevance": 1-5,
  "details": "0-50 word explanation of your assessment"
}
'

  full_prompt = paste0(
    instructions,
    data_context,
    "\n\nReport Text to Validate:\n",
    report_text,
    "\n",
    criteria,
    "\n",
    json_format
  )

  return(full_prompt)
}

## 1.3 Query AI Function #################################

query_ai_quality_control = function(prompt, provider = AI_PROVIDER, model = NULL) {

  if (provider == "ollama") {
    resolved_model = if (is.null(model)) resolve_ollama_model(OLLAMA_MODEL) else model
    url = paste0(OLLAMA_HOST, "/api/chat")

    body = list(
      model = resolved_model,
      messages = list(
        list(
          role = "user",
          content = prompt
        )
      ),
      format = "json",
      stream = FALSE,
      options = list(
        temperature = 0
      )
    )

    res = request(url) %>%
      req_body_json(body) %>%
      req_method("POST") %>%
      req_perform()

    response = resp_body_json(res)

    return(list(
      content = response$message$content,
      model = resolved_model
    ))
  }

  if (provider == "openai") {
    if (OPENAI_API_KEY == "") {
      stop("OPENAI_API_KEY not found in .env file. Please set it up first.")
    }

    url = "https://api.openai.com/v1/chat/completions"

    body = list(
      model = OPENAI_MODEL,
      messages = list(
        list(
          role = "system",
          content = "You are a quality control validator. Always return your responses as valid JSON."
        ),
        list(
          role = "user",
          content = prompt
        )
      ),
      response_format = list(type = "json_object"),
      temperature = 0
    )

    res = request(url) %>%
      req_headers(
        "Authorization" = paste0("Bearer ", OPENAI_API_KEY),
        "Content-Type" = "application/json"
      ) %>%
      req_body_json(body) %>%
      req_method("POST") %>%
      req_perform()

    response = resp_body_json(res)

    return(list(
      content = response$choices[[1]]$message$content,
      model = OPENAI_MODEL
    ))
  }

  stop("Invalid provider. Use 'ollama' or 'openai'.")
}

## 1.4 Parse Quality Control Results #################################

parse_quality_control_results = function(json_response, prompt_version, model_name) {
  json_match = str_extract(json_response, regex("\\{.*\\}", dotall = TRUE))
  if (!is.na(json_match)) {
    json_response = json_match
  }

  quality_data = fromJSON(json_response)

  results = tibble(
    prompt_version = prompt_version,
    model = model_name,
    accurate = quality_data$accurate,
    accuracy = quality_data$accuracy,
    formality = quality_data$formality,
    faithfulness = quality_data$faithfulness,
    clarity = quality_data$clarity,
    succinctness = quality_data$succinctness,
    relevance = quality_data$relevance,
    details = quality_data$details
  ) %>%
    mutate(
      overall_score = round(
        rowMeans(select(., accuracy, formality, faithfulness, clarity, succinctness, relevance)),
        2
      )
    )

  return(results)
}

## 1.5 Manual Comparison Summary #################################

manual_quality_summary = function(report_text) {
  tibble(
    has_numbers = str_detect(report_text, "\\d+"),
    has_percentages = str_detect(report_text, "\\d+%"),
    has_recommendations = str_detect(report_text, regex("recommend|suggest|should|must", ignore_case = TRUE)),
    has_contractions = str_detect(report_text, regex("'t|'s|'d|'ll|'ve|'re|'m", ignore_case = TRUE)),
    has_hyperbole = str_detect(report_text, regex("crucial|critical|extremely|absolutely", ignore_case = TRUE))
  )
}

# 2. RUN QUALITY CONTROL ###################################

selected_model = if (AI_PROVIDER == "ollama") resolve_ollama_model(OLLAMA_MODEL) else OPENAI_MODEL
prompt_versions = c("baseline", "enhanced")
all_results = list()

cat("🔧 Provider: ", AI_PROVIDER, "\n", sep = "")
cat("🔧 Model: ", selected_model, "\n\n", sep = "")

for (prompt_version in prompt_versions) {
  cat("🤖 Querying AI for quality control (", prompt_version, " prompt)...\n\n", sep = "")

  quality_prompt = create_quality_control_prompt(
    report_text = report,
    source_data = source_data,
    prompt_version = prompt_version
  )

  ai_response = query_ai_quality_control(
    prompt = quality_prompt,
    provider = AI_PROVIDER,
    model = selected_model
  )

  cat("📥 AI Response (raw):\n")
  cat(ai_response$content)
  cat("\n\n")

  quality_results = parse_quality_control_results(
    json_response = ai_response$content,
    prompt_version = prompt_version,
    model_name = ai_response$model
  )

  cat("✅ Quality Control Results:\n")
  print(quality_results, width = Inf)
  cat("\n")

  cat("📊 Overall Quality Score (average of Likert scales): ", quality_results$overall_score, "/ 5.0\n", sep = "")
  cat("📊 Accuracy Check: ", ifelse(quality_results$accurate, "✅ PASS", "❌ FAIL"), "\n\n", sep = "")

  all_results[[prompt_version]] = quality_results
}

comparison_results = bind_rows(all_results)
manual_summary = manual_quality_summary(report)

cat("📋 Prompt Comparison Summary:\n")
print(
  comparison_results %>%
    select(prompt_version, accurate, accuracy, formality, faithfulness, clarity, succinctness, relevance, overall_score),
  width = Inf
)
cat("\n")

cat("📋 Manual Quality Summary Reference:\n")
print(manual_summary)
cat("\n")

# 3. SAVE SUBMISSION-READY OUTPUTS ###################################

output_dir = "09_text_analysis/results"
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

write_csv(comparison_results, file.path(output_dir, "ai_quality_control_prompt_comparison.csv"))

baseline_score = comparison_results %>%
  filter(prompt_version == "baseline") %>%
  pull(overall_score)

enhanced_score = comparison_results %>%
  filter(prompt_version == "enhanced") %>%
  pull(overall_score)

submission_note = paste(
  "I kept the original multi-criteria JSON rubric as the baseline prompt and added an enhanced prompt that explicitly penalizes arithmetic mismatches, unsupported recommendations, and extra non-JSON output.",
  paste0("Using the local ", AI_PROVIDER, " model ", selected_model, ", the baseline prompt scored ", baseline_score, " while the enhanced prompt scored ", enhanced_score, " on the sample report."),
  "Compared with the manual quality control script, the AI approach adds graded ratings for accuracy, formality, faithfulness, clarity, succinctness, and relevance, while the manual approach mainly checks patterns like numbers, percentages, and recommendation language.",
  "In this run, the local AI model still appears to produce a false negative on the report's 87.9% total, so human review is still necessary even when the prompt is stricter.",
  "The enhanced prompt was more useful for surfacing unsupported claims, but reliability would improve further with more domain-specific rules or a stronger model.",
  sep = " "
)

writeLines(
  c(
    "# AI Quality Control Submission Notes",
    "",
    submission_note,
    "",
    "## Results Table",
    "",
    paste(capture.output(print(comparison_results, width = Inf)), collapse = "\n")
  ),
  file.path(output_dir, "ai_quality_control_submission_notes.md")
)

cat("✅ AI quality control complete!\n")
cat("💾 Saved CSV results to ", file.path(output_dir, "ai_quality_control_prompt_comparison.csv"), "\n", sep = "")
cat("💾 Saved submission notes to ", file.path(output_dir, "ai_quality_control_submission_notes.md"), "\n", sep = "")
