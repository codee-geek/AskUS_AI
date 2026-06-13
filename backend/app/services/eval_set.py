"""
Evaluation Set for RAGAS RAG Evaluation

RAGAS requires:
- query: The question
- ground_truth: Reference answer for context_recall metric

These QA pairs are derived from the indexed RAG paper.
"""

EVAL_SET = [
    {
        "query": "What is Retrieval-Augmented Generation (RAG)?",
        "ground_truth": "RAG (Retrieval-Augmented Generation) is a framework that combines parametric memory (LLM) with non-parametric memory (external database) to improve performance on knowledge-intensive tasks.",
    },
    {
        "query": "Who coined the term RAG and when?",
        "ground_truth": "Lewis et al. (2020) coined the term 'Retrieval-Augmented Generation (RAG)' and proposed a general framework.",
    },
    {
        "query": "What are the two main components of RAG?",
        "ground_truth": "The two main components are: 1) Parametric memory (the pre-trained LLM) and 2) Non-parametric memory (a separate database/vector store).",
    },
    {
        "query": "What is non-parametric memory in RAG?",
        "ground_truth": "Non-parametric memory refers to the external database or vector store that stores and retrieves relevant documents. It provides factual information to augment the LLM's knowledge.",
    },
    {
        "query": "What is parametric memory in RAG?",
        "ground_truth": "Parametric memory refers to the pre-trained LLM's internal knowledge stored in its neural network weights. It provides the generative capability.",
    },
    {
        "query": "What are hallucinations in LLMs?",
        "ground_truth": "Hallucinations are instances where LLMs generate outputs that are incorrect, misleading, or not grounded in the input context or factual knowledge.",
    },
    {
        "query": "What are knowledge-intensive tasks?",
        "ground_truth": "Knowledge-intensive tasks are tasks that require access to external factual information beyond the LLM's training data, such as question answering, fact verification, and information retrieval.",
    },
    {
        "query": "What is the difference between generative and discriminative tasks?",
        "ground_truth": "Generative tasks involve creating new content (like text generation), while discriminative tasks involve classifying or ranking existing content (like sentiment analysis or relevance scoring).",
    },
    {
        "query": "What previous work did Lewis et al acknowledge before RAG?",
        "ground_truth": "Lewis et al. acknowledged previous work including Guu et al. 2020, Karpukhin et al. 2020, and Perez et al. 2019 on integration of external data.",
    },
    {
        "query": "What is NELL and how does it relate to RAG?",
        "ground_truth": "NELL (Never-Ending Language Learning) is a continuous learning system that reads the web to extract knowledge. It's related to RAG as an early approach to combining retrieval with language models.",
    },
    {
        "query": "What is REALM?",
        "ground_truth": "REALM (Retrieval-Augmented Language Model) is an earlier approach that augmented language models with a knowledge retriever, serving as precursor work to RAG.",
    },
    {
        "query": "What is DPR?",
        "ground_truth": "DPR (Dense Passage Retrieval) is a method for retrieving relevant documents using dense vector representations instead of sparse term-based methods.",
    },
    {
        "query": "What is RAG-token and RAG-sequence?",
        "ground_truth": "RAG-token and RAG-sequence are two approaches where the retrieved passages are processed differently: RAG-token generates tokens based on each retrieved passage, while RAG-sequence generates a single sequence from the concatenated passages.",
    },
    {
        "query": "What are the three architectures in RAG?",
        "ground_truth": "The three RAG architectures are: 1) RAG-Token, 2) RAG-Sequence, and 3) FiD (Fusion-in-Decoder).",
    },
    {
        "query": "What is FiD (Fusion-in-Decoder)?",
        "ground_truth": "FiD (Fusion-in-Decoder) is an architecture where retrieved passages are encoded separately and then fused together in the decoder during generation.",
    },
    {
        "query": "What is EM (Exact Match) metric?",
        "ground_truth": "Exact Match (EM) is a binary metric that measures whether the predicted answer exactly matches the ground truth answer, commonly used in question answering evaluation.",
    },
    {
        "query": "What is F1 metric?",
        "ground_truth": "F1 is a metric that balances precision and recall, measuring the overlap between predicted and ground truth answers in token-level comparison.",
    },
    {
        "query": "What are the three benchmark datasets used for evaluation?",
        "ground_truth": "The three benchmark datasets are Natural Questions (NQ), TriviaQA, and WebQuestions, which are standard benchmarks for question answering systems.",
    },
    {
        "query": "What is Natural Questions (NQ)?",
        "ground_truth": "Natural Questions (NQ) is a benchmark dataset containing real user questions from Google search with corresponding answers from Wikipedia.",
    },
    {
        "query": "What is TriviaQA?",
        "ground_truth": "TriviaQA is a benchmark dataset containing question-answer pairs collected from trivia websites, used for evaluating question answering systems.",
    },
]


def get_eval_set():
    """Return the evaluation set."""
    return EVAL_SET
