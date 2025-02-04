# specdatri_reporting
The code base includes a collection of scripts and GitHub Actions designed to gather various metrics on RECETOX's impact.

## Local development

### Project setup
It is assumed you can clone and change directories into the development repo.
Create a virtualenv or conda environment (whatever your poison)

Once in the repos directory, activate your env then run the following command to install th needed python libraries.

> pip install -r .\requirements\local.txt

### Simulating Github Actions

You need [act](https://nektosact.com/) to test your code in development mode.
Install act for your chosen OS.
At your terminal, run (This simulates a GitHub action on your local device):

> act schedule


### Running tests:

#### Running with unittest
>  python -m unittest discover -s tests

#### Running with coverage
> coverage run -m unittest discover -s tests

> coverage report -m

> coverage html
