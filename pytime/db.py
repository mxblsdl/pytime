import sqlite3
from pathlib import Path


def init_db(clean: bool = False):
    # Init the DB

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
            print("Clearing existing database")
            cursor.execute("""drop table Time""")
            cursor.execute("""drop table Projects""")

        cursor.execute(
            """create table if not exists Time (
        date Text,
        project_id Integer,
        time Real,
        FOREIGN KEY (project_id) references Projects(id) 
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


# init_db(clean=True)

add_project("test2")
