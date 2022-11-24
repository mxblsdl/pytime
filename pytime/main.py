import typer

# from pytime.db import init_db
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box, print


app = typer.Typer(no_args_is_help=True)


"""

"""


def check_db_path():
    db_path = Path.home() / ".pytime/time.db"
    if not db_path.exists():
        raise Exception("DB does not exist! Run `pytime init` to resolve")
    return db_path


@app.callback()
def callback():
    """
    Time tracker app
    """


@app.command("init")
def db_init(clean: bool = typer.Option(False, "--clean", "-c", is_flag=True)):
    """
    Create an empty database and populate with a few tables
    """
    # Create folder for db if not exists
    db_path = Path.home() / ".pytime/time.db"
    db_path.parent.mkdir(exist_ok=True)

    if db_path.exists() and clean == False:
        print("Time database already exists\nNo action taken")
    else:
        print(f"Creating time database at\n{db_path}")
        # Create the initial connection
        con = sqlite3.connect(db_path)

        cursor = con.cursor()
        if clean:
            conf = typer.confirm(
                "This action will remove all data from database.\nAre you sure you want to proceed?"
            )
            if conf:
                print("Clearing existing database")
                cursor.execute("drop table Time")
                cursor.execute("drop table Projects")

        cursor.execute(
            """create table if not exists Time (
        date Text,
        project_id Integer,
        time Real
        )
        """
        )

        cursor.execute(
            """create table if not exists Projects (
        id INTEGER PRIMARY KEY,
        project TEXT
        )
        """
        )
    con.commit()
    con.close()


@app.command("add")
def add_project(proj: str = None):
    db_path = check_db_path()
    con = sqlite3.connect(db_path)

    cursor = con.cursor()

    # Check for existing project
    cursor.execute("select project from Projects")
    projects = cursor.fetchall()
    b = proj in [p[0] for p in projects]
    if b:
        print(f"Project {proj} already exists in DB! No action taken")
        return

    cursor.execute("insert into Projects (id, project) values (null, ?);", [proj])
    con.commit()
    con.close()
    print(f"Succesfully added *new* Project {proj}")


@app.command("log")
def log_time(
    date: str = typer.Argument(None),
    proj: str = typer.Option(..., prompt=True),
    time: float = typer.Option(..., prompt=True),
):
    """Log project time

    Args:
        date (str, optional): Date to add time for. Defaults to today
        proj (str, optional): Project name, entered from prompt
        time (float, optional): Time value in hours, entered from prompt
    """
    db_path = check_db_path()

    con = sqlite3.connect(db_path)
    cursor = con.cursor()

    proj_id = []
    while proj_id == []:
        try:
            cursor.execute("select id from Projects where project = ?", [proj])
            proj_id = cursor.fetchall()

            proj_id = proj_id[0][0]
        except:
            # TODO put in error check for proj not found
            # Ask to add project to list of projects
            print(f"Looks like {proj} is not being tracked")
            typer.prompt(f"Would you like to add {proj} to your projects?")
            add_project(proj)

        # raise Exception("Problem parsing project id")

    # Allow for dates other than today
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as ve:
            print(ve)
            return

    cursor.execute(
        "insert into Time (date, project_id, time) values (?, ?, ?)",
        [date, proj_id, time],
    )
    print(f"Successfully added {time} hour(s) to {proj}")
    con.commit()
    con.close()


# log_time("2022-11-23", "new_proj", 3.14)
# db_init(clean=True)
# app.init(clean=True)

# Create toy data
# add_project("amex")
# log_time("amex", 1.0, "2022-11-21")
# log_time("amex", 4.0, "2022-11-21")
# log_time("amex", 6.0, "2022-11-22")
# log_time("amex", 3.0, "2022-11-08")
# log_time("amex", 4.0, "2022-11-09")


def print_week(day: str) -> None:
    dt = datetime.strptime(day, "%Y-%m-%d")
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6)
    print(f"Monday {start.strftime('%Y-%m-%d')}")
    print(f"Sunday {end.strftime('%Y-%m-%d')}")


# Testing out creating a table report in console


@app.command("report")
def time_report(
    weeks_back: int = typer.Argument(
        default=0, help="Weeks back to generate report", show_default=True
    )
):
    """
    Generate a console report of time for the week
    """
    console = Console()

    # Calculate start of week
    start, end = get_start_end_date(weeks_back)

    con = sqlite3.connect(check_db_path())
    cursor = con.cursor()

    sql = """
    SELECT date, project, time
    FROM Time
    JOIN Projects
    ON Time.project_id = Projects.id
    WHERE date >= ? AND date < ?;
    """

    # Run SQL with start of week and convert to list
    res = cursor.execute(
        sql,
        [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")],
    )
    res = [r for r in res]

    # Calculate total hours
    total_hours = sum(r[2] for r in res)

    # Init table
    table = create_table(start, total_hours)

    for i in range(len(res)):
        table.add_row(res[i][0], res[i][1], str(res[i][2]))

        try:
            res[i + 1]
        except:
            table.add_section()
            break

        if res[i][0] != res[i + 1][0]:
            table.add_section()

    console.print(table)


def create_table(start, total_hours):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="dim")
    table.add_column(
        "Project", Text.from_markup("Total", justify="right"), style="green"
    )
    table.add_column("Time", footer=str(total_hours), justify="right")
    table.title = f"Week Starting {start.strftime('%Y-%m-%d')}"
    table.caption = "Made with :snake:"
    table.show_footer = True
    table.box = box.SIMPLE
    return table


def get_start_end_date(weeks_back):
    dt = datetime.strftime(datetime.today(), "%Y-%m-%d")
    dt = datetime.strptime(dt, "%Y-%m-%d")
    start = dt - timedelta(days=dt.weekday()) - timedelta(weeks=weeks_back)
    end = start + timedelta(days=6)
    return start, end


# time_report(weeks_back=1)
