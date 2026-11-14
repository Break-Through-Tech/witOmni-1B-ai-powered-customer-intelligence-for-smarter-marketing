# WitOmni Customer Return Simulator

Interactive Streamlit web app based on the supplied WitOmni notebook.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit displays (usually http://localhost:8501).

## Share as a website

Upload `app.py` and `requirements.txt` to a GitHub repository. Deploy the repository on Streamlit Community Cloud at https://share.streamlit.io/ and share the resulting URL with your advisor.

## Data/model details

On first launch, the app downloads the public UCI Online Retail dataset and trains an XGBoost model using the baseline hyperparameters in the notebook (100 estimators, max depth 3, learning rate 0.01). It uses the nine features in the notebook's final feature-engineering comparison. This is **not** the saved best tuned estimator, which was not included in the notebook upload. The app measures and displays its own test ROC-AUC. Internet access is required on initial load.
