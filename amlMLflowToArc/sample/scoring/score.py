# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
"""This module will load mlflow model and do prediction."""

import os
import mlflow
import logging
import json

def init():
    global iris_model
    iris_model = mlflow.lightgbm.load_model(os.getenv('AZUREML_MODEL_DIR') + "/model")
    logging.info("Model loaded")


def run(input_data):
    logging.info("input data: %s", input_data)
    data = json.loads(input_data)["data"]
    pred = iris_model.predict(data)
    return pred.tolist()

if __name__ == "__main__":
    init()
    input_data = '{"data": [[1,2,3,4]]}'
    result = run(input_data)
    print(result)