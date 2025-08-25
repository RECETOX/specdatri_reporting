# specdatri_reporting
The code base includes a collection of scripts and GitHub Actions designed to gather various metrics on RECETOX's impact.

## Local development

### Project setup
It is assumed you can clone and change directories into the development repo.
Create a virtualenv or conda environment (whatever your poison).

Once in the repos directory, activate your env then run the following command to install the needed python libraries.

> pip install -r .\requirements\local.txt

### Simulating Github Actions

You need [act](https://nektosact.com/) to test your code in development mode.
Install act for your chosen OS.
At your terminal, run (This simulates a GitHub action on your local device):

> act --secret-file .env schedule

### Things to note

1: Do not push local development changes from `tmp` folder and `reports` folder. In fact do not edit them at all !!!

2: When testing with `act` do not use a token that has the permission to make push requests else your test data will mess with "production" data.

3: When testing with `act` know that the push may fail due to the fact that you can't directly push to main.

4: Always, I repeat always devlop on another branch not main and never push directly to main.

5: You need tokens to test the code locally, place said tokens in `example.env` and change the filename to `.env`

6: When testing with act files will be created in the docker image but never written to your file system.

### Running tests:

#### Running with unittest
> python -m unittest discover -s tests

#### Running with coverage
> coverage run -m unittest discover -s tests

> coverage report -m

> coverage html
