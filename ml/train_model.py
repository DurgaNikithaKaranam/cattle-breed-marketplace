import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

data = pd.read_csv("breed_dataset.csv")

le_purpose = LabelEncoder()
le_milk = LabelEncoder()
le_breed = LabelEncoder()

data["purpose"] = le_purpose.fit_transform(data["purpose"])
data["milk_yield"] = le_milk.fit_transform(data["milk_yield"])
data["breed"] = le_breed.fit_transform(data["breed"])

X = data[["purpose", "milk_yield"]]
y = data["breed"]

model = DecisionTreeClassifier()
model.fit(X, y)

joblib.dump(model, "breed_model.pkl")
joblib.dump(le_purpose, "purpose_encoder.pkl")
joblib.dump(le_milk, "milk_encoder.pkl")
joblib.dump(le_breed, "breed_encoder.pkl")

print("Model trained successfully")