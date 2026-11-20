import numpy as np   # heavy imports run at INIT (cold start) - deliberate
import pandas as pd
def handler(event, context):
    df = pd.DataFrame({"x": np.arange(200_000)})
    return {"sum": int((df["x"] ** 2).sum())}
