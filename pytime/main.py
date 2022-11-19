import typer

# from pytime.db import init_db
from pathlib import Path
import sqlite3
from rich import print

app = typer.Typer(no_args_is_help=True)


"""
!TODO
- add time function

"""

@app.callback()
def callback():
    """
    Time tracker app
    """


@app.command()
def main():
    """
    Awesome Portal Gun
    """
    typer.echo("Works better!!!")


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
                cursor.execute("""drop table Time""")
                cursor.execute("""drop table Projects""")

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


@app.command("add")
def add_project(proj: str = None):
    db_path = Path.home() / ".pytime/time.db"
    if not db_path.exists():
        print("DB does not exist! Run `pytime init` to resolve")
        return

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
    print(f"Succesfully added *new* Project {proj}")


# db_init(clean=True)
# app.init(clean=True)
