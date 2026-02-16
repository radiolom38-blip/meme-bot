import pandas as pd
from sklearn.linear_model import LogisticRegression
import os
import joblib

MODEL_FILE = "model.pkl"
DATA_FILE = "data.csv"

def train_model():
    if not os.path.exists(DATA_FILE):
        return None

    df = pd.read_csv(DATA_FILE)

    if len(df) < 20:
        return None

    X = df[['vsr','bp','liq','txns','whale','hype']]
    y = df['pumped']

    model = LogisticRegression()
    model.fit(X, y)

    joblib.dump(model, MODEL_FILE)
    return model


def load_model():
    if os.path.exists(MODEL_FILE):
        return joblib.load(MODEL_FILE)
    return None


def predict(model, vsr, bp, liq, txns, whale, hype):
    if not model:
        return 50

    prob = model.predict_proba([[vsr,bp,liq,txns,whale,hype]])[0][1]
    return round(prob * 100)


def save_training_data(row):
    df = pd.DataFrame([row])

    if os.path.exists(DATA_FILE):
        df.to_csv(DATA_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(DATA_FILE, index=False)
