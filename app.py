from flask import Flask, render_template, request, redirect, url_for

import csv
import os

app = Flask(__name__)

# Helper functions


def read_info():
    # get current absolute directory name of app.py
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    # generate the absolute file path for subjects.csv
    file_name = os.path.join(curr_dir, "static/subjects.csv")

    subjs_info = []

    with open(file_name, "r") as f:
        csvreader = csv.reader(f)
        header = next(csvreader)  # remove header line of file

        for row in csvreader:
            subjs_info.append(row)

    return subjs_info


subjs_info = read_info()

# print(subjs_info)


def score_to_gpa_grade(score):
    conversion_table = {
        85: (5.0, "A*"), 75: (4.0, "A1"), 70: (3.5, "A2"),
        65: (3.0, "B3"), 60: (2.5, "B4"), 55: (2.0, "C5"),
        50: (1.5, "C6"), 45: (1.0, "D7"), 40: (0.5, "E8"),
        0: (0.0, "F9"),
    }

    for key in conversion_table:
        if score >= key:
            return conversion_table[key]


def calc_gpa_normal(all_subjs):
    total = 0
    weightage = 0

    for row in all_subjs:
        if row[1] == "ss":
            total += row[7] * 0.5
            weightage += 0.5
        else:
            total += row[7]
            weightage += 1.0

    return round(total/weightage, 2)


def calc_gpa_sec4(all_subjs):
    # assume gpa is calculated using
    # 2 languages, maths, cid, ss (0.5)
    # 1 best sci, 1 best hum, 1 best other

    best_sci = ["subj", 0]
    best_hum = ["subj", 0]
    best_other = ["subj", 0]

    # find best sci and hum first
    for row in all_subjs:
        if row[2] == "Science" and row[5] > best_sci[1]:
            best_sci = [row[1], row[5]]
        elif row[2] == "Humanities" and row[1] != "ss" \
                and row[5] > best_hum[1]:
            best_hum = [row[1], row[5]]

    # print(all_subjs)
    # print(best_sci, best_hum)

    # find best other
    for row in all_subjs:
        if row[2] in ["Science", "Humanities", "Maths"] \
            and row[1] != best_sci[0] and row[1] != best_hum[0] \
                and row[1] != "ss":
            # is one of the sci/hum/maths, but not the best sci/hum
            if row[5] > best_other[1]:
                best_other = [row[1], row[5]]

    # print(best_other)

    # calc gpa and indicate if counted or double-counted
    total_gpa = 0
    total_weight = 0

    for row in all_subjs:
        if row[4] == "T":
            # all compulsory subjects
            if row[1] == "ss":
                total_gpa += row[7] * 0.5
                total_weight += 0.5
            else:
                total_gpa += row[7]
                total_weight += 1.0
            row.append("C")

        if row[1] == best_sci[0] \
                or row[1] == best_hum[0] \
                or row[1] == best_other[0]:
            # one of the best sci/hum/other
            total_gpa += row[7]
            total_weight += 1.0

            if row[1] == "maths":
                row[-1] = "D"
            else:
                row.append("C")

    for row in all_subjs:
        # add uncounted status
        if row[-1] not in ["C", "D"]:
            row.append("U")

    gpa = round(total_gpa / total_weight, 2)

    # print(all_subjs)

    return gpa


# Flask routing functions

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/opt_subjs/")
def opt_subjs():
    level = request.args["level"]
    if level in "12":
        # if sec 1 or 2, no need select opt subjs
        return redirect(url_for("process_results", level=level))
    else:
        # if sec 3 or 4, go to opt subjs selection
        compul_subjs = []
        opt_sci_subjs = []
        opt_hum_subjs = []

        for row in subjs_info:
            if level in row[3] and row[4] == "T":
                # compulsory subj
                compul_subjs.append(row)
            elif level in row[3] and row[4] == "F":
                # optional subj
                if row[2] == "Science":
                    opt_sci_subjs.append(row)
                elif row[2] == "Humanities":
                    opt_hum_subjs.append(row)

        # print(compul_subjs, opt_sci_subjs, opt_hum_subjs)

        return render_template(
            "opt_subjs.html",
            level=level,
            compul_subjs=compul_subjs,
            opt_sci_subjs=opt_sci_subjs,
            opt_hum_subjs=opt_hum_subjs
        )


@app.route("/process_results/", methods=["GET", "POST"])
def process_results():
    if request.method == "GET":
        # GET request, render page 3 (score)
        level = request.args["level"]
        all_subjs = []

        if level in "12":
            # sec 1 or 2, only have compulsory subjs
            for row in subjs_info:
                if level in row[3]:
                    all_subjs.append(row)
        else:
            # sec 3 or 4, read the optional subjs
            # print(request.args)
            sci_subjs = request.args.getlist('opt_sci_subjs')
            hum_subjs = request.args.getlist('opt_hum_subjs')

            # print(sci_subjs, hum_subjs)
            for row in subjs_info:
                if level in row[3] and row[4] == "T":
                    # compulsory subj for sec 3/4
                    all_subjs.append(row)
                elif row[1] in sci_subjs or row[1] in hum_subjs:
                    # opt subj is selected by user
                    all_subjs.append(row)

        print(all_subjs)

        return render_template(
            "score.html",
            level=level,
            all_subjs=all_subjs)
    else:
        # POST request, render page 4 (results)
        level = request.form["level"]
        all_subjs = []

        for key in request.form:
            if key != "level":
                # it's a subj

                # look through subjs_info to find the relevant row of this subj
                # add the row to all subj
                for row in subjs_info:
                    if row[1] == key:
                        # row.copy() will create a duplicate list
                        # without changing the original
                        new_row = row.copy()

                        score = int(request.form[key])
                        gpa, grade = score_to_gpa_grade(score)

                        new_row.append(score)
                        new_row.append(grade)
                        new_row.append(gpa)

                        all_subjs.append(new_row)

                        # there is exactly 1 match, can break after found
                        break

        if level != "4":
            gpa = calc_gpa_normal(all_subjs)
        else:
            gpa = calc_gpa_sec4(all_subjs)

        return render_template(
            "result.html",
            level=level,
            gpa=gpa,
            all_subjs=all_subjs)


# run app
if __name__ == "__main__":
    app.run(debug=True)
