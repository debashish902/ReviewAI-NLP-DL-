import json
import sys
import traceback

from contextlib import redirect_stdout


# ============================================================
# SMARTREVIEW AI - PERSISTENT PYTHON WORKER
# ============================================================

# IMPORTANT:
# Standard output is reserved exclusively for JSON responses.
# Diagnostic messages are directed to standard error.
# This allows Node.js to parse responses reliably.

print(
    "SMARTREVIEW AI worker starting...",
    file=sys.stderr
)


# ============================================================
# LOAD THE EXISTING INFERENCE ENGINE
# ============================================================

try:

    # analyze_review.py may print initialization messages.
    # Redirect these messages to stderr so stdout contains
    # only the JSON responses expected by Node.js.

    with redirect_stdout(sys.stderr):

        from analyze_review import analyze_review

    print(
        "AI inference engine loaded successfully.",
        file=sys.stderr
    )

except Exception:

    traceback.print_exc(
        file=sys.stderr
    )

    sys.exit(1)


# ============================================================
# PROCESS REQUESTS
# ============================================================

print(
    "AI worker is ready.",
    file=sys.stderr
)


while True:

    raw_line = sys.stdin.readline()

    if not raw_line:
        break

    raw_line = raw_line.strip()

    if not raw_line:
        continue

    request_id = None

    try:

        # ----------------------------------------------------
        # PARSE THE INCOMING JSON REQUEST
        # ----------------------------------------------------

        request = json.loads(
            raw_line
        )

        request_id = request.get(
            "id"
        )

        review = request.get(
            "review"
        )


        # ----------------------------------------------------
        # VALIDATE THE REVIEW
        # ----------------------------------------------------

        if not isinstance(review, str):

            raise ValueError(
                "The 'review' field must be a string."
            )

        review = review.strip()

        if not review:

            raise ValueError(
                "Review text cannot be empty."
            )

        if len(review) > 10000:

            raise ValueError(
                "Review cannot exceed 10000 characters."
            )


        # ----------------------------------------------------
        # RUN CALIBRATED ASPECT-BASED SENTIMENT ANALYSIS
        # ----------------------------------------------------

        # IMPORTANT:
        # Keep inference logs away from stdout.
        # Node.js expects stdout to contain JSON responses only.

        with redirect_stdout(sys.stderr):

            result = analyze_review(review)


        # ----------------------------------------------------
        # BUILD THE SUCCESSFUL RESPONSE
        # ----------------------------------------------------

        response = {
            "id": request_id,
            "success": True,
            "data": result
        }


    except Exception as error:

        # Keep debugging information away from JSON stdout.

        print(
            f"AI analysis failed: {error}",
            file=sys.stderr
        )

        traceback.print_exc(
            file=sys.stderr
        )

        response = {
            "id": request_id,
            "success": False,
            "error": str(error)
        }


    # ========================================================
    # RETURN EXACTLY ONE JSON LINE
    # ========================================================

    try:

        response_json = json.dumps(
            response,
            ensure_ascii=False
        )

        sys.stdout.write(
            response_json + "\n"
        )

        sys.stdout.flush()

    except Exception:

        traceback.print_exc(
            file=sys.stderr
        )


# ============================================================
# SHUTDOWN
# ============================================================

print(
    "AI worker stopped.",
    file=sys.stderr
)