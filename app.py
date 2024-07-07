from flask import Flask, render_template, url_for, redirect, request, session, flash
import os
import joblib
import pandas as pd
from datetime import timedelta
from core import cleaner, trainer, predicter

# App Instance, setting a secret key and the time of a session.
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.permanent_session_lifetime = timedelta(minutes=5)

# Setting a folder where the script could save the csv files and models.
UPLOAD_FOLDER = 'uploads'
MODEL_FOLDER = 'models'

# Function to clean up the folders with files from past sessions.
def clear_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f'Error eliminating {file_path}: {e}')

# Cleaning thee folders for a new session in the app.
@app.before_first_request
def init_app():
    session.clear()
    clear_folder(UPLOAD_FOLDER)
    clear_folder(MODEL_FOLDER)

# Function to prevent errors from text inputs of the users.
def normalize_and_validate_columns(columns):
    return [col.strip() for col in columns.split(',') if col.strip()]

# Principal route of the web app.
@app.route("/", methods=["POST", "GET"])
def main():
    if request.method == "POST":
        if "csvfile" in request.files:
            csvfile = request.files["csvfile"]
            if csvfile:
                csv_path = os.path.join(UPLOAD_FOLDER, csvfile.filename)
                csvfile.save(csv_path)
                session["csvfile"] = csv_path
                session.pop("cleaned_csv", None)
                flash('File uploaded successfully', 'success')
                return redirect(url_for("main"))
            else:
                flash('Please select a file to upload', 'error')
                return redirect(url_for("main"))
            
        elif request.form.get("clean"):
            csv_path = session.get("csvfile")
            if csv_path:
                cleaned_df = cleaner(csv_path)
                cleaned_df_path = os.path.join(UPLOAD_FOLDER, "cleaned_" + os.path.basename(csv_path))
                cleaned_df.to_csv(cleaned_df_path, index=False)
                session["cleaned_csv"] = cleaned_df_path
                flash('File cleaned successfully', 'success')
                return redirect(url_for("main"))
            else:
                flash('No file uploaded to clean', 'error')
                return redirect(url_for("main"))
            
        elif request.form.get("train"):
            cleaned_csv_path = session.get("cleaned_csv")
            target_column = request.form.get("target-column")
            feature_columns_input = request.form.get("feature-columns")
            if cleaned_csv_path and target_column and feature_columns_input:
                feature_columns = normalize_and_validate_columns(feature_columns_input)
                if feature_columns:
                    cleaned_df = pd.read_csv(cleaned_csv_path)
                    model, coef_dict = trainer(cleaned_df, target_column, feature_columns)
                    
                    model_path = os.path.join(MODEL_FOLDER, "linear_regression_model.pkl")
                    joblib.dump(model, model_path)

                    session["model"] = model_path
                    session["feature_columns"] = ', '.join(feature_columns)
                    session["training_success"] = True
                    session["coef_dict"] = coef_dict
                    session["target_column"] = target_column
                    flash('Model trained successfully', 'success')
                    return redirect(url_for("main"))
                else:
                    flash('Please provide valid feature columns', 'error')
                    return redirect(url_for("main"))
            else:
                flash('Please provide target column and feature columns', 'error')
                return redirect(url_for("main"))
            
        elif request.form.get("predict"):
            model_path = session.get("model")
            feature_columns = session.get("feature_columns").split(', ')
            example_values_input = request.form.get("x-values")
            if model_path and feature_columns and example_values_input:
                try:
                    example_values = [float(val.strip()) for val in example_values_input.split(',')]
                    if len(example_values) == len(feature_columns):
                        model = joblib.load(model_path)
                        cleaned_csv_path = session.get("cleaned_csv")
                        cleaned_df = pd.read_csv(cleaned_csv_path)
                        X_test = cleaned_df[feature_columns]
                        y_test = cleaned_df[session["target_column"]]
                        
                        prediction, rmse = predicter(model, example_values, feature_columns, X_test, y_test)
                        
                        session["prediction"] = prediction
                        session["rmse"] = rmse
                        session["example_values"] = ', '.join(map(str, example_values))
                        flash('Prediction made successfully', 'success')
                        return redirect(url_for("main"))
                    else:
                        flash('Number of values does not match number of features', 'error')
                        return redirect(url_for("main"))
                except ValueError:
                    flash('Please provide valid numeric values for prediction', 'error')
                    return redirect(url_for("main"))
            else:
                flash('Please provide all required values for prediction', 'error')
                return redirect(url_for("main"))
            
    csvfile = session.get("csvfile")
    cleaned_csv = session.get("cleaned_csv")
    training_success = session.get("training_success")
    coef_dict = session.get("coef_dict")
    prediction = session.pop("prediction", None)
    rmse = session.pop("rmse", None)
    data = None
    cleaned_data = None
    if csvfile:
        df = pd.read_csv(csvfile, nrows=25)
        data = df.to_html()
    if cleaned_csv:
        df_cleaned = pd.read_csv(cleaned_csv, nrows=25)
        cleaned_data = df_cleaned.to_html()
    return render_template("index.html", data=data, cleaned_data=cleaned_data, training_success=training_success, coef_dict=coef_dict, prediction=prediction, rmse=rmse)

@app.route("/home")
def home():
    return redirect(url_for("main"))

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)