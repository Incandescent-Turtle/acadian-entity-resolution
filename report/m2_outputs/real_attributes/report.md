# RQ1 retrieval — m2_real_attributes

## t0_clean

| method | n_queries | candidate_recall | mean_candidates | recall@1 | recall@5 | recall@10 | mrr |
|---|---|---|---|---|---|---|---|
| exact_name | 500 | 0.996 | 356.214 | 0.876 | 0.992 | 0.996 | 0.929 |
| tfidf | 500 | 0.996 | 356.214 | 0.984 | 0.996 | 0.996 | 0.990 |
| sentence_transformer | 500 | 0.996 | 356.214 | 0.994 | 0.996 | 0.996 | 0.995 |
| rgcn_k0 | 500 | 0.996 | 356.214 | 0.972 | 0.996 | 0.996 | 0.984 |

## t1_name

| method | n_queries | candidate_recall | mean_candidates | recall@1 | recall@5 | recall@10 | mrr |
|---|---|---|---|---|---|---|---|
| exact_name | 500 | 0.994 | 103.574 | 0.420 | 0.692 | 0.798 | 0.543 |
| tfidf | 500 | 0.994 | 103.574 | 0.952 | 0.990 | 0.994 | 0.969 |
| sentence_transformer | 500 | 0.994 | 103.574 | 0.864 | 0.964 | 0.976 | 0.907 |
| rgcn_k0 | 500 | 0.994 | 103.574 | 0.484 | 0.676 | 0.746 | 0.574 |

## t2_dates

| method | n_queries | candidate_recall | mean_candidates | recall@1 | recall@5 | recall@10 | mrr |
|---|---|---|---|---|---|---|---|
| exact_name | 500 | 0.996 | 356.214 | 0.696 | 0.868 | 0.924 | 0.774 |
| tfidf | 500 | 0.996 | 356.214 | 0.800 | 0.882 | 0.904 | 0.838 |
| sentence_transformer | 500 | 0.996 | 356.214 | 0.760 | 0.846 | 0.878 | 0.803 |
| rgcn_k0 | 500 | 0.996 | 356.214 | 0.828 | 0.936 | 0.954 | 0.878 |

## all

| method | n_queries | candidate_recall | mean_candidates | recall@1 | recall@5 | recall@10 | mrr |
|---|---|---|---|---|---|---|---|
| exact_name | 1500 | 0.995 | 272.001 | 0.664 | 0.851 | 0.906 | 0.749 |
| tfidf | 1500 | 0.995 | 272.001 | 0.912 | 0.956 | 0.965 | 0.932 |
| sentence_transformer | 1500 | 0.995 | 272.001 | 0.873 | 0.935 | 0.950 | 0.901 |
| rgcn_k0 | 1500 | 0.995 | 272.001 | 0.761 | 0.869 | 0.899 | 0.812 |
