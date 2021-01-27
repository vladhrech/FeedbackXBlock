# coding: utf-8
"""
This is an XBlock designed to allow people to provide feedback on our
course resources, and to think and synthesize about their experience
in the course.
"""

import cgi
import random

import pkg_resources
import six
from django.utils.translation import ugettext_lazy as _
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Boolean, Dict, Float, Integer, List, Scope, String
from xblockutils.resources import ResourceLoader

loader = ResourceLoader(__name__)


# We provide default text which is designed to elicit student thought. We"d
# like instructors to customize this to something highly structured (not
# "What did you think?" and "How did you like it?".
DEFAULT_FREEFORM = _("What did you learn from this? What was missing?")
DEFAULT_LIKERT = _("How would you rate this as a learning experience?")
DEFAULT_PLACEHOLDER = _("Take a little bit of time to reflect here. "
                        "Research shows that a meaningful synthesis will help "
                        "you better understand and remember material from this "
                        "course.")
DEFAULT_ICON = "num"

ASSESSMENTS_NUMBER = 11


@XBlock.needs("i18n")
class FeedbackXBlock(XBlock):
    """
    This is an XBlock -- eventually, hopefully an aside -- which
    allows you to feedback content in the course. We've wanted this for a
    long time, but Dartmouth finally encourage me to start to build
    this.
    """
    prompt = Dict(
        default={
            "freeform": DEFAULT_FREEFORM,
            "likert": DEFAULT_LIKERT,
            "placeholder": DEFAULT_PLACEHOLDER,
            "scale_text": {i: "" for i in range(1, ASSESSMENTS_NUMBER)},
            "icon_set": DEFAULT_ICON,
            "zero_likert": ""
        },
        scope=Scope.settings,
        help=_("Freeform user prompts"),
        xml_node=True
    )

    prompts_choice = Integer(
        default=-1, scope=Scope.user_state,
        help=_("Random number generated for p. -1 if uninitialized")
    )

    user_vote = Integer(
        default=-1, scope=Scope.user_state,
        help=_("How user voted. -1 if didn't vote")
    )

    # pylint: disable=invalid-name
    p = Float(
        default=100, scope=Scope.settings,
        help=_("What percent of the time should this show?")
    )

    p_user = Float(
        default=-1, scope=Scope.user_state,
        help=_("Random number generated for p. -1 if uninitialized")
    )

    vote_aggregate = List(
        default=None, scope=Scope.user_state_summary,
        help=_("A list of user votes")
    )

    user_freeform = String(default="", scope=Scope.user_state, help=_("Feedback"))

    enable_text_area_answer = Boolean(
        default=False, scope=Scope.settings,
        help=_("Enables ability to add text feedback for a student")
    )

    enable_zero_grade = Boolean(
        default=False, scope=Scope.settings,
        help=_("Enables ability to add extra 0 grade")
    )

    display_name = String(
        display_name=_("Display Name"),
        default=_("Provide Feedback"),
        help=_("The display name for this component."),
        scope=Scope.settings
    )

    @classmethod
    def resource_string(cls, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the FeedbackXBlock, shown to students
        when viewing courses.
        """
        # Figure out which prompts we show. We set self.prompts_choice to
        # the index of the prompts. We set it if it is out of range (either
        # uninitiailized, or incorrect due to changing list length). Then,
        # we grab the prompts, prepopulated with defaults.
        propts_size = ASSESSMENTS_NUMBER

        if self.prompts_choice < 0 or self.prompts_choice >= propts_size:
            self.prompts_choice = random.randint(0, propts_size - 1)

        indices = range(propts_size) if self.enable_zero_grade else range(1, propts_size)
        active_vote = ["checked" if i == self.user_vote else "" for i in indices]

        # Confirm that we do have vote totals (this may be uninitialized
        # otherwise). This should probably go into __init__ or similar.
        self.init_vote_aggregate()
        votes = self.vote_aggregate if self.enable_zero_grade else self.vote_aggregate[1:]

        icon_path_template = {
            "inactive": "public/numbers/i{set}{i}.png",
            "active": "public/numbers/a{set}{i}.png"
        }

        # We grab the icons. This should move to a Filesystem field so
        # instructors can upload new ones
        def get_url(icon_type, icon_number):
            """
            Helper function to generate the URL for the icons shown in the
            tool. Takes the type of icon (active, inactive, etc.) and
            the number of the icon.

            Note that some icon types may not be actively used in the
            styling. For example, at the time of this writing, we do
            selected through CSS, rather than by using those icons.
            """
            icon_file = icon_path_template[icon_type].format(i=icon_number, set=self.prompt["icon_set"])
            return self.runtime.local_resource_url(self, icon_file)

        inactive_urls = [get_url("inactive", i) for i in range(1, propts_size)]
        active_urls = [get_url("active", i) for i in range(1, propts_size)]

        _ = self.runtime.service(self, "i18n").ugettext
        if self.user_vote != -1:

            response = _("Thank you for voting!")
        else:
            response = ""

        zero_likert_item = [self.prompt["zero_likert"], get_url("inactive", 0), get_url("active", 0)]

        context = {
            "user_freeform": self.user_freeform,
            "scale": self.prompt["scale_text"],
            "inactive_urls": inactive_urls,
            "active_urls": active_urls,
            "zero_likert_item": zero_likert_item,
            "freeform_prompts": _(self.prompt["freeform"]),
            "likert_prompts": _(self.prompt["likert"]),
            "response": response,
            "placeholder": _(self.prompt["placeholder"]),
            "enable_text_area_answer": self.enable_text_area_answer,
            "votes": votes,
            "active_vote": active_vote,
            "enable_zero_grade": self.enable_zero_grade,
            "ugettext": _
        }

        rendered = loader.render_mako_template(
            "static/html/feedback.html",
            context=context
        )

        # We initialize self.p_user if not initialized -- this sets whether
        # or not we show it. From there, if it is less than odds of showing,
        # we set the fragment to the rendered XBlock. Otherwise, we return
        # empty HTML. There ought to be a way to return None, but XBlocks
        # doesn't support that.
        if self.p_user == -1:
            self.p_user = random.uniform(0, 100)

        frag = Fragment(rendered) if self.p_user < self.p else Fragment("")

        # Finally, we do the standard JS+CSS boilerplate. Honestly, XBlocks
        # ought to have a sane default here.
        frag.add_css(self.resource_string("static/css/feedback.css"))
        frag.add_javascript(self.resource_string("static/js/src/feedback.js"))
        frag.initialize_js("FeedbackXBlock")
        return frag

    def studio_view(self, context):
        """
        Create a fragment used to display the edit view in the Studio.
        """
        context = self.prompt
        context["display_name"] = self.display_name
        context["enable_text_area_answer"] = self.enable_text_area_answer
        context["enable_zero_grade"] = self.enable_zero_grade
        html = loader.render_django_template(
            "static/html/studio_view.html",
            context=context,
            i18n_service=self.runtime.service(self, "i18n")
        )
        frag = Fragment(html)
        js_str = self.resource_string("static/js/src/studio.js")
        frag.add_javascript(six.text_type(js_str))
        frag.initialize_js("FeedbackBlock", {"icon_set": self.prompt["icon_set"]})
        return frag

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        for item in ["freeform", "likert", "placeholder", "icon_set"]:
            item_submission = data.get(item)
            if item_submission and len(item_submission) > 0:
                self.prompt[item] = cgi.escape(item_submission)

        self.prompt["scale_text"] = dict(sorted(data["scale_text"].items()))
        self.display_name = data["display_name"]
        self.enable_text_area_answer = data["enable-text-area-answer"]
        self.prompt["zero_likert"] = data["zero_likert"]
        self.enable_zero_grade = data["enable_zero_grade"]

        return {"result": "success"}

    def init_vote_aggregate(self):
        """
        There are a lot of places we read the aggregate vote counts. We
        start out with these uninitialized. This guarantees they are
        initialized. We'd prefer to do it this way, rather than default
        value, since we do plan to not force scale length to be 5 in the
        future.
        """
        if not self.vote_aggregate:
            self.vote_aggregate = [0] * ASSESSMENTS_NUMBER

    def vote(self, data):
        """
        Handle voting
        """
        # Make sure we're initialized
        self.init_vote_aggregate()

        # Remove old vote if we voted before
        if self.user_vote != -1:
            self.vote_aggregate[self.user_vote] -= 1

        self.user_vote = data['vote']
        self.vote_aggregate[self.user_vote] += 1

    @XBlock.json_handler
    def feedback(self, data, suffix=''):
        """
        Allow students to submit feedback, both numerical and
        qualitative. We only update the specific type of feedback
        submitted.

        We return the current state. While this is not used by the
        client code, it is helpful for testing. For staff users, we
        also return the aggregate results.
        """
        _ = self.runtime.service(self, "i18n").ugettext

        if "freeform" not in data and "vote" not in data:
            response = {"success": False, "response": _("Please, vote!")}
            self.runtime.publish(self, "edx.feedbackxblock.nothing_provided", {})
        if "vote" in data:
            response = {"success": True, "response": _("Thank you for voting!")}
            self.runtime.publish(
                self,
                "edx.feedbackxblock.likert_provided",
                {
                    "old_vote": self.user_vote,
                    "new_vote": data["vote"]
                }
            )
            self.vote(data)
        if "freeform" in data:
            response = {"success": True, "response": _("Thank you for your feedback!")}
            self.runtime.publish(
                self,
                "edx.feedbackxblock.freeform_provided",
                {
                    "old_freeform": self.user_freeform,
                    "new_freeform": data["freeform"]
                }
            )
            self.user_freeform = data["freeform"]

        response["freeform"] = self.user_freeform
        response["vote"] = self.user_vote

        if self.is_staff():
            response["aggregate"] = self.vote_aggregate

        return response

    @staticmethod
    def workbench_scenarios():
        """
        A canned scenario for display in the workbench.

        We have three blocks. One shows up all the time (for testing). The
        other two show up 50% of the time.
        """
        return [
            ("FeedbackXBlock",
             """<vertical_demo>
                <feedback p="100"/>
                <feedback p="50"/>
                <feedback p="50"/>
                </vertical_demo>
             """),
        ]

    def is_staff(self):
        """
        Return self.xmodule_runtime.user_is_staff if available

        This is not a supported part of the XBlocks API in all
        runtimes, and this is a workaround so something reasonable
        happens in both workbench and edx-platform
        """
        if hasattr(self, "xmodule_runtime") and \
           hasattr(self.xmodule_runtime, "user_is_staff"):
            return self.xmodule_runtime.user_is_staff
        else:
            # In workbench and similar settings, always return true
            return True
