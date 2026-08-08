from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np

def rmse(obs, sim): 
    return mean_squared_error(obs, sim)
def mae(obs, sim): 
    return mean_absolute_error(obs,sim)
def bias(obs, sim): 
    return np.mean(obs - sim)
def r2(obs, sim):
    return r2_score(obs,sim)
def correlation(obs, sim):
     return np.corrcoef(obs, sim)[0, 1]




def phase_shift(obs, sim):
     ...
def iav(obs, sim):
        ...



def calculate_metrics(obs, sim):

    return {
        "RMSE": rmse(obs, sim),
        "MAE": mae(obs, sim),
        "Bias": bias(obs, sim),
        "R2": r2(obs, sim),
        "r": correlation(obs, sim),
    }

def print_metrics(results): 
    print("\n--------------------------")
    print(" PERFORMANCE CLASSIC VS OBS ") 
    print("----------------------------") 
    
    print(f"RMSE : {results['RMSE']:.2f} W m-2") 
    print(f"MAE : {results['MAE']:.2f} W m-2") 
    print(f"Bias : {results['Bias']:.2f} W m-2") 
    print(f"r : {results['r']:.3f}") 
    print(f"R2 : {results['R2']:.3f}")