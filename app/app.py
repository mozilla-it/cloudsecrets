# -*- coding: utf-8 -*-
import datetime
import json
import time

import sqlalchemy
from bs4 import BeautifulSoup as BSoup
from flask import Flask, render_template
from flask import flash, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from wtforms import Form, TextField, validators
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config["SECRET_KEY"] = "SjdnUends821Jsdlkvxh391ksdODnejdDw"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.secret_key = "dev"

bootstrap = Bootstrap(app)
db = SQLAlchemy(app)


class Configuration(db.Model):
    __tablename__ = "configuration"
    id = db.Column(db.Integer, primary_key=True)
    cloudsnap_email = db.Column(db.String)
    cloudsnap_password = db.Column(db.String)


class Workflow(db.Model):
    __tablename__ = "workflow"
    id = db.Column(db.Integer, primary_key=True)
    workflow_option = db.Column(db.String)
    workflow_text = db.Column(db.String)


class StepFailure(db.Model):
    __tablename__ = "step_failures"
    id = db.Column(db.Integer, primary_key=True)
    entity = db.Column(db.String)
    name = db.Column(db.String)
    timestamp = db.Column(db.DateTime)
    state = db.Column(db.String)
    url = db.Column(db.String)
    instance = db.Column(db.String)
    retried = db.Column(db.Integer)
    dismissed = db.Column(db.Boolean)


class PausedJobs(db.Model):
    __tablename__ = "paused_jobs"
    id = db.Column(db.Integer, primary_key=True)
    entity = db.Column(db.String)
    name = db.Column(db.String)
    timestamp = db.Column(db.DateTime)
    state = db.Column(db.String)
    url = db.Column(db.String)
    instance = db.Column(db.String)
    retried = db.Column(db.Integer)
    dismissed = db.Column(db.Boolean)


class SuccessfulJobs(db.Model):
    __tablename__ = "successful_jobs"
    id = db.Column(db.Integer, primary_key=True)
    entity = db.Column(db.String)
    name = db.Column(db.String)
    timestamp = db.Column(db.DateTime)
    state = db.Column(db.String)
    url = db.Column(db.String)
    instance = db.Column(db.String)


class Statistics(db.Model):
    __tablename__ = "statistics"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    successful = db.Column(db.Integer)
    failed = db.Column(db.Integer)
    retried = db.Column(db.Integer)
    paused = db.Column(db.Integer)


class CloudSnap:
    def __init__(self, driver, configuration):
        self.driver = driver
        self.configuration = configuration
        self.login_url = "https://app.cloudsnap.com/users/sign_in"

    def login(self):
        self.driver.get(self.login_url)
        self.driver.implicitly_wait(5)
        self.driver.find_element_by_id("user_email").send_keys(
            self.configuration.cloudsnap_email
        )
        self.driver.find_element_by_id("user_password").send_keys(
            self.configuration.cloudsnap_password
        )
        submit_button = self.driver.find_element_by_name("commit")
        submit_button.send_keys(Keys.ENTER)
        # self.driver.find_element_by_xpath(
        #     "/html/body/div/div/div/form/div[2]/div[3]/input"
        # ).send_keys(Keys.ENTER)

    def get_workflows(self):
        self.driver.get("https://app.cloudsnap.com/workflow_instances")
        self.driver.implicitly_wait(10)
        select_box = self.driver.find_element_by_id("workflow_id")
        options = [x for x in select_box.find_elements_by_tag_name("option")]
        for element in options:
            text = element.get_attribute("text")
            option = element.get_attribute("value")
            exists = (
                db.session.query(Workflow.id).filter_by(workflow_option=option).scalar()
                is not None
            )
            if exists:
                continue
            workflow = Workflow()
            workflow.workflow_option = option
            workflow.workflow_text = text
            db.session.add(workflow)
            db.session.commit()
        return Workflow.query.order_by(Workflow.workflow_option).all()

    def get_paused_jobs(self, workflow):
        """
        This function acquires the first page of paused jobs and returns them to the caller.  No
        attempt was made at pagination for this PoC.
        :param workflow:
        :return: paused job dictionary
        """
        select_workflow = Select(self.driver.find_element_by_id("workflow_id"))
        select_workflow.select_by_visible_text(workflow.workflow_text)

        # Paused filter
        select_paused_state = Select(self.driver.find_element_by_id("q_c_0_a_0_name"))
        select_paused_state.select_by_visible_text("Paused")

        select_is_true_state = Select(self.driver.find_element_by_id("q_c_0_p"))
        select_is_true_state.select_by_visible_text("is true")

        from selenium.webdriver.common.action_chains import ActionChains

        element = self.driver.find_element_by_xpath(
            '//*[@id="search_form"]/div/div[2]/span[2]'
        )
        ActionChains(self.driver).move_to_element(element).perform()
        element.click()

        time.sleep(10)

        bs_obj = BSoup(self.driver.page_source, "html.parser")

        try:
            rows = bs_obj.find_all("table")[0].find("tbody").find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 0:
                    continue
                job_name = cells[0].get_text()
                entity_name = job_name[job_name.find("(") + 1 : job_name.find(")")]
                string_datetime = time.strptime(
                    cells[1].get_text(), "%m/%d/%Y %H:%M:%S %Z"
                )
                job_date = datetime.datetime.fromtimestamp(time.mktime(string_datetime))
                week = datetime.datetime.now() - datetime.timedelta(days=7)
                if job_date < week:
                    continue
                job_state = cells[2].find("i")["title"]
                if job_state != "Paused":
                    continue
                workflow_url = (
                    "https://app.cloudsnap.com"
                    + cells[4].find_all("a", href=True)[0]["href"]
                )
                workflow_instance = (
                    "https://app.cloudsnap.com"
                    + cells[5].find_all("a", href=True)[0]["href"]
                )
                exists = (
                    db.session.query(PausedJobs.id)
                    .filter_by(timestamp=job_date)
                    .scalar()
                    is not None
                )
                if exists:
                    continue
                paused = PausedJobs()
                paused.name = job_name
                paused.entity = entity_name
                paused.timestamp = job_date
                paused.state = job_state
                paused.url = workflow_url
                paused.instance = workflow_instance
                db.session.add(paused)
                db.session.commit()
            return PausedJobs.query.all()
        except:
            return None

    def get_succesful_jobs(self, workflow):
        """
        This function acquires the first page of paused jobs and returns them to the caller.  No
        attempt was made at pagination for this PoC.
        :param workflow:
        :return: paused job dictionary
        """
        select_workflow = Select(self.driver.find_element_by_id("workflow_id"))
        select_workflow.select_by_visible_text(workflow.workflow_text)

        # Paused filter
        select_paused_state = Select(self.driver.find_element_by_id("q_c_0_a_0_name"))
        select_paused_state.select_by_visible_text("Success")

        select_is_true_state = Select(self.driver.find_element_by_id("q_c_0_p"))
        select_is_true_state.select_by_visible_text("is true")

        from selenium.webdriver.common.action_chains import ActionChains

        element = self.driver.find_element_by_xpath(
            '//*[@id="search_form"]/div/div[2]/span[2]'
        )
        ActionChains(self.driver).move_to_element(element).perform()
        element.click()

        time.sleep(10)

        bs_obj = BSoup(self.driver.page_source, "html.parser")
        try:
            rows = bs_obj.find_all("table")[0].find("tbody").find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 0:
                    continue
                job_name = cells[0].get_text()
                entity_name = job_name[job_name.find("(") + 1 : job_name.find(")")]
                string_datetime = time.strptime(
                    cells[1].get_text(), "%m/%d/%Y %H:%M:%S %Z"
                )
                job_date = datetime.datetime.fromtimestamp(time.mktime(string_datetime))
                week = datetime.datetime.now() - datetime.timedelta(days=7)
                if job_date < week:
                    continue
                job_state = cells[2].find("i")["title"]
                if job_state != "Success!":
                    continue
                workflow_url = (
                    "https://app.cloudsnap.com"
                    + cells[4].find_all("a", href=True)[0]["href"]
                )
                workflow_instance = (
                    "https://app.cloudsnap.com"
                    + cells[5].find_all("a", href=True)[0]["href"]
                )
                exists = (
                    db.session.query(PausedJobs.id)
                    .filter_by(timestamp=job_date)
                    .scalar()
                    is not None
                )
                if exists:
                    continue
                successful = SuccessfulJobs()
                successful.name = job_name
                successful.entity = entity_name
                successful.timestamp = job_date
                successful.state = job_state
                successful.url = workflow_url
                successful.instance = workflow_instance
                db.session.add(successful)
                db.session.commit()
            return SuccessfulJobs.query.all()
        except:
            return None

    def get_step_failure_jobs(self, workflow):
        """
        This function acquires the first page of paused jobs and returns them to the caller.  No
        attempt was made at pagination for this PoC.
        :param workflow:
        :return: paused job dictionary
        """
        select_workflow = Select(self.driver.find_element_by_id("workflow_id"))
        select_workflow.select_by_visible_text(workflow.workflow_text)

        # Paused filter
        select_paused_state = Select(self.driver.find_element_by_id("q_c_0_a_0_name"))
        select_paused_state.select_by_visible_text("Step failure")

        select_is_true_state = Select(self.driver.find_element_by_id("q_c_0_p"))
        select_is_true_state.select_by_visible_text("is true")

        from selenium.webdriver.common.action_chains import ActionChains

        element = self.driver.find_element_by_xpath(
            '//*[@id="search_form"]/div/div[2]/span[2]'
        )
        ActionChains(self.driver).move_to_element(element).perform()
        element.click()

        time.sleep(10)

        bs_obj = BSoup(self.driver.page_source, "html.parser")
        try:
            rows = bs_obj.find_all("table")[0].find("tbody").find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 0:
                    continue
                job_name = cells[0].get_text()
                entity_name = job_name[job_name.find("(") + 1 : job_name.find(")")]
                string_datetime = time.strptime(
                    cells[1].get_text(), "%m/%d/%Y %H:%M:%S %Z"
                )
                job_date = datetime.datetime.fromtimestamp(time.mktime(string_datetime))
                week = datetime.datetime.now() - datetime.timedelta(days=7)
                if job_date < week:
                    continue
                job_state = cells[2].find("i")["title"]
                if job_state != "Step Failure":
                    continue
                workflow_url = (
                    "https://app.cloudsnap.com"
                    + cells[0].find_all("a", href=True)[0]["href"]
                )
                workflow_instance = (
                    "https://app.cloudsnap.com"
                    + cells[5].find_all("a", href=True)[0]["href"]
                )
                step_failure = StepFailure()
                step_failure.timestamp = job_date
                step_failure.url = workflow_url
                step_failure.state = job_state
                step_failure.name = job_name
                step_failure.entity = entity_name
                db.session.add(step_failure)
                db.session.commit()
            return StepFailure.query.all()
        except:
            return None


class ReusableForm(Form):
    email = TextField("email:", validators=[validators.required()])
    password = TextField("password:", validators=[validators.required()])


@app.route("/", methods=["GET", "POST"])
def index():
    form = ReusableForm(request.form)
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        configuration = Configuration.query.filter_by(cloudsnap_email=email).first()
        if configuration is not None:
            configuration.cloudsnap_password = password
            db.session.commit()
            flash(f"Updated: {email}")
        else:
            configuration = Configuration()
            configuration.cloudsnap_email = email
            configuration.cloudsnap_password = password
            configuration.crawling_interval = int(crawl_frequency)
            configuration.crawling_unit = crawl_unit
            db.session.add(configuration)
            db.session.commit()
            flash(f"Added: {email}")
        return render_template("index.html", form=form)
    else:
        return render_template("index.html", form=form)


@app.route("/paused", methods=["GET"])
def paused_jobs():
    paused = PausedJobs.query.order_by(PausedJobs.timestamp.desc()).all()
    return render_template("paused.html", paused_jobs=paused)


@app.route("/step", methods=["GET"])
def step_failures():
    failures = StepFailure.query.order_by(StepFailure.timestamp.desc()).all()
    return render_template("step.html", step_failures=failures)


@app.route("/successes", methods=["GET"])
def successes():
    successful_jobs = SuccessfulJobs.query.order_by(
        SuccessfulJobs.timestamp.desc()
    ).all()
    return render_template("success.html", successes=successful_jobs)


@app.route("/statistics", methods=["GET"])
def statistics():
    Statistics.query.delete()
    db.session.commit()

    for successful_job in SuccessfulJobs.query.order_by(
        SuccessfulJobs.timestamp.desc()
    ).all():
        row_date = successful_job.timestamp.date()
        if (
            db.session.query(Statistics).filter(Statistics.date == row_date).count()
            != 0
        ):
            continue
        paused_jobs = (
            db.session.query(PausedJobs)
            .filter(sqlalchemy.func.date(PausedJobs.timestamp) == row_date)
            .all()
        )
        step_failure_jobs = (
            db.session.query(StepFailure)
            .filter(sqlalchemy.func.date(StepFailure.timestamp) == row_date)
            .all()
        )
        success_jobs = (
            db.session.query(SuccessfulJobs)
            .filter(sqlalchemy.func.date(SuccessfulJobs.timestamp) == row_date)
            .all()
        )
        statistic = Statistics()
        statistic.date = row_date

        # Paused Jobs
        if len(paused_jobs) == 0:
            if paused_jobs is None:
                statistic.paused = 0
            else:
                statistic.paused = len(paused_jobs)
        else:
            if paused_jobs is None:
                statistic.paused += 0
            else:
                statistic.paused = len(paused_jobs)

        # Step Failure Jobs
        if len(step_failure_jobs) == 0:
            if step_failure_jobs is None:
                statistic.failed = 0
            else:
                if step_failure_jobs is None:
                    statistic.failed += 0
                else:
                    statistic.failed = len(step_failure_jobs)
        else:
            statistic.failed = len(step_failure_jobs)

        # Successful Jobs
        if len(success_jobs) == 0:
            if success_jobs is None:
                statistic.successful = 0
            else:
                statistic.successful = len(success_jobs)
        else:
            if success_jobs is None:
                statistic.successful += 0
            else:
                statistic.successful = len(success_jobs)
        db.session.add(statistic)
        db.session.commit()

    stats = Statistics.query.order_by(Statistics.date.desc()).all()
    return render_template("statistics.html", statistics=stats)


@app.route("/crawl", methods=["GET"])
def crawl():
    # from webdriver_manager.firefox import GeckoDriverManager
    # from selenium.webdriver.firefox.options import Options
    #
    # options = Options()
    # options.headless = False
    # driver = webdriver.Firefox(
    #     options=options, executable_path=GeckoDriverManager().install()
    # )

    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.headless = True
    driver = webdriver.Chrome(
        chrome_options=options, executable_path=ChromeDriverManager().install()
    )
    configuration = Configuration.query.first()
    cloudsnap = CloudSnap(driver, configuration)
    cloudsnap.login()
    workflows = cloudsnap.get_workflows()
    for workflow in workflows:
        cloudsnap.get_succesful_jobs(workflow)
        cloudsnap.get_paused_jobs(workflow)
        cloudsnap.get_step_failure_jobs(workflow)
    driver.quit()
    return render_template("crawl.html")


if __name__ == "__main__":
    db.create_all()
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=crawl, trigger="interval", hours=24)
    scheduler.start()
    app.run(debug=True, port=5001)
