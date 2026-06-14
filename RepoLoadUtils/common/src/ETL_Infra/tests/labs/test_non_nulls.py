import pandas as pd


def Test(df: pd.DataFrame, si, codedir: str, workdir: str):

    if len(df) == 0:
        return True

    cols = [x for x in df.columns if x == "pid" or "value_" in x or "time_" in x]
    sig_name = df["signal"].iloc[0]
    zero_allowed = pd.read_csv(
        "rep_signals/lab_zero_value_allowed.txt", names=["signal"]
    )

    for col in cols:
        df[col] = (
            df[col].astype(float).round(6)
        )  # no need to have more then 6 digits in labs

        if ("value" in col) & (sig_name in zero_allowed.signal.tolist()):
            continue

        null_cnt = len(df[df[col].isnull()])

        if null_cnt / len(df) > 0.001:
            print(
                "Failed! There are %d(%2.3f%%) missing values for signal %s in col %s"
                % (null_cnt, 100 * null_cnt / len(df), sig_name, col)
            )
            return False

        if null_cnt > 0:
            print(
                "There are %d(%2.3f%%) missing values for signal %s in col %s"
                % (null_cnt, 100 * null_cnt / len(df), sig_name, col)
            )

        df.drop(df.loc[df[col].isnull()].index, inplace=True)  # clean nulls
        df.reset_index(drop=True, inplace=True)

    print("Done testing nulls in signal %s" % (sig_name))

    return True
