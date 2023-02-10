import typer

from clockify_api_client.client import ClockifyAPIClient
from datetime import datetime, timedelta
from dateutil import tz
import pandas as pd
from pathlib import Path
from rich.table import Table
from rich.text import Text
from rich import box, print


app = typer.Typer(
    help="Visualize the clockify API",
    epilog="Made for run with :snake:",
    rich_markup_mode="markdown",
    no_args_is_help=True,
)


@app.command("clear")
def api_clear():
    config_file = Path.home() / ".clock.config"
    if config_file.exists():
        config_file.unlink()
        print("API config file has been removed")
    else:
        print("No config file found")
    return


def api_prompt(API_URL: str = "api.clockify.me/v1"):
    """
    check if api key exists
    if not, ask to enter api key
    check api is correct
    if enter ask to save api key
    """
    config_file = Path.home() / ".clock.config"
    if not config_file.exists():
        print("API Key has not been configured.")
        api = typer.prompt("Enter your API key")
        print(f"Using API version: {API_URL}")
        try:
            client = ClockifyAPIClient().build(api, API_URL)
        except:
            print("Problem with API key\nMake sure your key was entered correctly")
            raise typer.Abort()
        print("API key entered successfully!")
        res = typer.prompt("Would you like to save the API for future use? (y/n)")

        while res.lower() not in ["y", "n"]:
            res = typer.prompt("Please enter either 'y' or 'n'")

        if res.lower() == "n":
            return client
        else:
            config_file.touch()
            config_file.write_text(f"""API_KEY={api}""")
            return client
    else:
        print("Using stored API Credentials")
        api_text = config_file.read_text()
        api_text = api_text.split("=")
        api = api_text[1]
        try:
            client = ClockifyAPIClient().build(api, API_URL)
        except:
            print("Problem with API key\nMake sure your key was entered correctly")
            raise typer.Abort()
        return client


@app.command("proj")
def get_project_durations(
    weeks_back: int = typer.Option(0, "--back", "-b", is_flag=True),
    weekly: bool = typer.Option(True, "--week", "-w", is_flag=True),
) -> None:
    config_file = Path.home() / ".clock.config"
    if not config_file.exists():
        print("API Key has not been configured.")
        typer.Abort()

    # initialize client
    client = api_prompt()

    # Return the workspace id and user id
    # This assumes there is only one workspace for the user
    workspace_id, user_id = get_ids(client)
    projs = client.projects.get_projects(workspace_id)

    # get all projects
    projs = client.projects.get_projects(workspace_id)

    # Get all time entries
    # Params passed as dictionary items that filter results
    out = pd.DataFrame()

    for proj in projs:
        dt = datetime.today()
        start = dt - timedelta(days=dt.weekday()) - timedelta(weeks=weeks_back)
        start = start.replace(hour=0)  # set to beginning of day
        end = start + timedelta(days=6)

        # Make API call from start date
        entries = client.time_entries.get_time_entries(
            workspace_id,
            user_id,
            params={
                "project": proj["id"],
                "page-size": 500,
                "start": start.isoformat() + "Z",
                "end": end.isoformat() + "Z",
            },
        )

        # Parse results by project
        e = [e["timeInterval"] for e in entries]
        df = pd.DataFrame(e)

        if not df.empty:
            df = create_cols(df, proj)

            # Here I would groupby and summarize the duration
            # Then append this project with the output
            if weekly:
                df = df.groupby(["name", "date"]).agg({"duration": "sum"}).reset_index()
                out = pd.concat([out, df])
                continue

            table = create_table(
                start, end, total_hours=round(df["duration"].sum(), ndigits=2)
            )

            for row in df.itertuples():
                table.add_row(row.date, row.name, str(row.duration))

            print(table)

    if weekly:
        out = out.sort_values("date").reset_index()
        out["duration"] = round(out["duration"], 2)

        table = create_table(
            start, end, total_hours=round(out["duration"].sum(), ndigits=2)
        )
        for ind in out.index:
            table.add_row(
                out.loc[ind]["date"],
                out.loc[ind]["name"],
                str(out.loc[ind]["duration"]),
            )

            try:
                out.loc[ind + 1]
            except:
                subtotal(out, table, ind)
                table.add_section()
                break

            if out.loc[ind]["date"] != out.loc[ind + 1]["date"]:
                subtotal(out, table, ind)
                table.add_section()
        print(table)


def subtotal(out, table, ind):
    day_total = out[out["date"] == out.loc[ind]["date"]]
    table.add_row("", "Subtotal", str(round(day_total["duration"].sum(), 2)))


def create_cols(df: pd.DataFrame, proj: str = ""):
    df["start"] = pd.to_datetime(df["start"], format="%Y-%m-%dT%H:%M:%SZ", utc=True)
    df["end"] = pd.to_datetime(df["end"], format="%Y-%m-%dT%H:%M:%SZ", utc=True)

    # Convert to local time
    df["start"] = df["start"].dt.tz_convert(tz.tzlocal())
    df["end"] = df["end"].dt.tz_convert(tz.tzlocal())

    diff = df["end"] - df["start"]
    df["duration"] = round(diff.dt.total_seconds() / 3600, 2)
    # Add a less specific date for the table
    df["date"] = df["start"].dt.strftime("%Y-%m-%d")

    # conditionally add proj name
    if proj != "":
        df["name"] = proj["name"]

    return df


def get_ids(client):
    workspaces = client.workspaces.get_workspaces()  # Returns list of workspaces.
    workspace_id = workspaces[0]["id"]
    user_id = client.users.get_current_user()["id"]
    return workspace_id, user_id


# Helpers
# Create table method
def create_table(start, end, total_hours):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="dim")
    table.add_column(
        "Project", Text.from_markup("Total", justify="right"), style="green"
    )
    table.add_column("Time", footer=str(total_hours), justify="right")
    table.title = f"Week {start.strftime('%Y-%m-%d')} - {end.strftime('%Y-%m-%d')}"
    table.caption = "Made with :snake:"
    table.show_footer = True
    table.box = box.SIMPLE
    return table
