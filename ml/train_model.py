import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

path = os.path.dirname(__file__)
data = pd.read_csv(os.path.join(path,"breed_dataset.csv"))

encoders = {}

for col in data.columns:
    le = LabelEncoder()
    data[col] = le.fit_transform(data[col])
    encoders[col] = le

X = data.drop("breed",axis=1)
y = data["breed"]

model = RandomForestClassifier(n_estimators=200,random_state=42)
model.fit(X,y)

joblib.dump(model, os.path.join(path,"breed_model.pkl"))
joblib.dump(encoders, os.path.join(path,"encoders.pkl"))

print("MODEL TRAINED SUCCESSFULLY")