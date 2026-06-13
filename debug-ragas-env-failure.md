# Debug Session: ragas-env-failure [OPEN]

## Goal
- Repair the evaluation runtime enough to execute RAGAS and show results.

## Current Symptoms
- `OPENAI_API_KEY` is missing for the backend runtime.
- The current Python environment has incompatible LangChain package versions.
- Importing the app stack fails before RAGAS execution can start.

## Hypotheses
1. Installing `ragas<0.2.0` downgraded `langchain-core`, which broke `langchain-huggingface`.
2. The project runtime and evaluation runtime need separate dependency environments.
3. The backend does not load an `.env` file from the project root in the way we expect during command execution.
4. RAGAS cannot run at all in this session without a valid `OPENAI_API_KEY`.

## Evidence Collected
- `ImportError: cannot import name 'ModelProfile' from 'langchain_core.language_models'`
- `OPENAI_API_KEY: missing`
- Main app runtime was restored by reinstalling repo requirements.
- An isolated evaluation venv at `/tmp/ragas-eval-venv` successfully imports:
  - `ragas==0.1.22`
  - `langchain==0.2.17`
  - `langchain-core==0.2.43`
  - `langchain-community==0.2.19`

## Next Steps
- Start the backend with the repaired main environment and verify retrieval still works.
- Obtain a valid `OPENAI_API_KEY` for RAGAS judge calls.
- Run RAGAS from the isolated evaluation environment against the backend output.
