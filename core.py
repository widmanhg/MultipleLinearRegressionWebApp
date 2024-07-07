import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

def cleaner(raw_csv, categorical_threshold=10):
    df = pd.read_csv(raw_csv)

    df.dropna(axis=1, how='all', inplace=True)  # Remove completely empty columns.
    df.dropna(axis=0, how='all', inplace=True)  # Remove completely empty rows.

    # Fill missing values in numerical columns with the column's mean.
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].mean())

    # Fill missing values in text columns with an empty string.
    text_cols = df.select_dtypes(include=[object]).columns
    df[text_cols] = df[text_cols].fillna('')

    # Detect and encode categorical columns
    categorical_cols = []
    non_categorical_text_cols = []
    categorical_positions = {}

    for col in text_cols:
        num_unique_values = df[col].nunique()
        if num_unique_values <= categorical_threshold and num_unique_values > 1:
            categorical_cols.append(col)
            categorical_positions[col] = df.columns.get_loc(col)
        elif num_unique_values > categorical_threshold:
            non_categorical_text_cols.append(col)

    # Encode categorical columns
    df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

    # Drop non-categorical text columns
    df.drop(columns=non_categorical_text_cols, inplace=True)

    # Reinsert the encoded columns in the original positions
    new_columns = df.columns.tolist()
    for col in categorical_cols:
        start_idx = categorical_positions[col]
        encoded_cols = [c for c in new_columns if c.startswith(col + '_')]
        for i, encoded_col in enumerate(encoded_cols):
            new_columns.remove(encoded_col)
            new_columns.insert(start_idx + i, encoded_col)
    df = df[new_columns]

    df.drop_duplicates(inplace=True)  # Remove duplicates.

    return df

def trainer(cleaned_df, target_column, feature_columns):
    # Separate features (X) and target variable (y)
    X = cleaned_df[feature_columns]
    y = cleaned_df[target_column]

    # Initialize the linear regression model
    model = LinearRegression()

    # Train the model with the data
    model.fit(X, y)

    # Extract the coefficients
    intercept = model.intercept_
    coefficients = model.coef_

    # Create a dictionary to store coefficients with their corresponding feature names
    coef_dict = {'Intercept': intercept}
    for feature, coef in zip(feature_columns, coefficients):
        coef_dict[feature] = coef

    return model, coef_dict

def predicter(model, example_values, feature_columns, X_test, y_test):
    if len(example_values) != len(feature_columns):
        raise ValueError("The number of example values must match the number of feature columns")

    # Convert example values to a 2D array as the model expects multiple samples
    example_values_df = pd.DataFrame([example_values], columns=feature_columns)
    
    # Predict using the trained model
    prediction = model.predict(example_values_df)
    
    # Calculate RMSE
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    return prediction[0], rmse