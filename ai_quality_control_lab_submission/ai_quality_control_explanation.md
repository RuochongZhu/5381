# AI Quality Control Submission Notes

I kept the original multi-criteria JSON rubric as the baseline prompt and added an enhanced prompt that explicitly penalizes arithmetic mismatches, unsupported recommendations, and extra non-JSON output. Using the local ollama model qwen2.5:3b, the baseline prompt scored 3.5 while the enhanced prompt scored 3.17 on the sample report. Compared with the manual quality control script, the AI approach adds graded ratings for accuracy, formality, faithfulness, clarity, succinctness, and relevance, while the manual approach mainly checks patterns like numbers, percentages, and recommendation language. In this run, the local AI model still appears to produce a false negative on the report's 87.9% total, so human review is still necessary even when the prompt is stricter. The enhanced prompt was more useful for surfacing unsupported claims, but reliability would improve further with more domain-specific rules or a stronger model.

## Results Table

# A tibble: 2 × 11
  prompt_version model      accurate accuracy formality faithfulness clarity
  <chr>          <chr>      <lgl>       <int>     <int>        <int>   <int>
1 baseline       qwen2.5:3b FALSE           2         3            4       4
2 enhanced       qwen2.5:3b FALSE           2         3            2       3
  succinctness relevance
         <int>     <int>
1            3         5
2            4         5
  details                                                                       
  <chr>                                                                         
1 The report misinterprets the data by stating that Light Trucks and Cars/Bikes…
2 The report misinterprets the data by suggesting that Light Trucks and Cars/Bi…
  overall_score
          <dbl>
1          3.5 
2          3.17
