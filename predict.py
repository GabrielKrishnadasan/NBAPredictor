import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.feature_selection import SequentialFeatureSelector
from sklearn.linear_model import RidgeClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score

df = pd.read_csv('nba_games.csv', index_col = 0)
df = df.sort_values("date")
df = df.reset_index(drop=True)

#Removed useless columns
del df["mp.1"]
del df["mp_opp.1"]
del df["index_opp"]

def add_target(team):
    team["target"] = team["won"].shift(-1)
    return team

#Data cleaning and adding the target column
df = df.groupby("team", group_keys=False).apply(add_target)

#Attempt to prevent SettingWithCopyWarning, didnt work :(
df = df.copy()

df["target"][pd.isnull(df["target"])] = 2
df["target"] = df["target"].astype(int, errors="ignore")

#Removing null columns
nulls = pd.isnull(df)
nulls = nulls.sum()
nulls = nulls[nulls > 0]
valid_columns = df.columns[~df.columns.isin(nulls.index)]

df = df[valid_columns].copy()

#Machine learning setup
rc = RidgeClassifier(alpha=1)
split = TimeSeriesSplit(n_splits = 3)

#sets up sfs to choose predictor features, can mess around with the 30 to change prediction rate success
sfs = SequentialFeatureSelector(rc, n_features_to_select=30, direction="forward", cv=split)

#cleaning non numerical data
removed_columns = ["season", "date", "won", "target", "team", "team_opp"]
selected_columns = df.columns[~df.columns.isin(removed_columns)]

#Scales all numerical data to 0-1
scaler = MinMaxScaler()
df[selected_columns] = scaler.fit_transform(df[selected_columns])

#Runs sfs to get best predictors
sfs.fit(df[selected_columns], df["target"])

#Saves 30 best predictors
predictors = list(selected_columns[sfs.get_support()])

#This fucntion is to make sure we are only using past data to infer on the selected game
def backtest(data, model, predictors, start=2, step=1):
    all_predictions = []
    
    seasons = sorted(data["season"].unique())
    
    for i in range(start, len(seasons), step):
        season = seasons[i]
        train = data[data["season"] < season]
        test = data[data["season"] == season]
        
        model.fit(train[predictors], train["target"])
        
        preds = model.predict(test[predictors])
        preds = pd.Series(preds, index=test.index)
        combined = pd.concat([test["target"], preds], axis=1)
        combined.columns = ["actual", "prediction"]
        
        all_predictions.append(combined)
    return pd.concat(all_predictions)

predictions = backtest(df, rc, predictors)

#Baseline prediction, without any rolling data, or opponent/home data
temp = accuracy_score(predictions["actual"], predictions["prediction"])
print(temp)

df_rolling = df[list(selected_columns) + ["won", "team", "season"]]

#Calculates the rolling averages over the last 5 or n games
def find_team_averages(team):
    rolling = team.rolling(5).mean()
    return rolling

df_rolling = df_rolling.groupby(["team", "season"], group_keys=False).apply(find_team_averages)

rolling_cols = [f"{col}_5" for col in df_rolling.columns]
df_rolling.columns = rolling_cols
df = pd.concat([df, df_rolling], axis=1)

#Removes the first 5 or n games, as we dont have any rolling data for them
df = df.dropna()

#To set up for knowing who the next opponent is
def shift_col(team, col_name):
    next_col = team[col_name].shift(-1)
    return next_col

def add_col(df, col_name):
    return df.groupby("team", group_keys=False).apply(lambda x: shift_col(x, col_name))

df["home_next"] = add_col(df, "home")
df["team_opp_next"] = add_col(df, "team_opp")
df["date_next"] = add_col(df, "date")

df = df.copy()

#data frame with the updated data
full = df.merge(df[rolling_cols + ["team_opp_next", "date_next", "team"]], left_on=["team", "date_next"], right_on=["team_opp_next", "date_next"])

removed_columns = list(full.columns[full.dtypes == "object"]) + removed_columns

selected_columns = full.columns[~full.columns.isin(removed_columns)]
sfs.fit(full[selected_columns], full["target"])

predictors = list(selected_columns[sfs.get_support()])

predictions = backtest(full, rc, predictors)

#Second test with rolling data and opponent data
temp = accuracy_score(predictions["actual"], predictions["prediction"])
print(temp)