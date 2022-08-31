import logging

from sendgrid import SendGridAPIClient, SendGridException
from sendgrid.helpers.mail import Mail

from ...account import events as account_events
from ...celeryconf import app
from ...graphql.core.utils import from_global_id_or_none
from . import SendgridConfiguration

logger = logging.getLogger(__name__)

CELERY_RETRY_BACKOFF = 60
CELERY_RETRY_MAX = 5


def send_email(configuration: SendgridConfiguration, template_id, payload):
    recipient_email = payload["recipient_email"]
    sendgrid_client = SendGridAPIClient(configuration.api_key)
    from_email = (configuration.sender_address, configuration.sender_name)
    message = Mail(from_email=from_email, to_emails=recipient_email)
    message.dynamic_template_data = payload
    message.template_id = template_id
    sendgrid_client.send(message)


@app.task(
    autoretry_for=(SendGridException,),
    retry_backoff=CELERY_RETRY_BACKOFF,
    retry_kwargs={"max_retries": CELERY_RETRY_MAX},
    compression="zlib",
)
def send_account_confirmation_email_task(payload: dict, configuration: dict):
    configuration = SendgridConfiguration(**configuration)
    send_email(
        configuration=configuration,
        template_id=configuration.account_confirmation_template_id,
        payload=payload,
    )


@app.task(
    autoretry_for=(SendGridException,),
    retry_backoff=CELERY_RETRY_BACKOFF,
    retry_kwargs={"max_retries": CELERY_RETRY_MAX},
    compression="zlib",
)
def send_password_reset_email_task(payload: dict, configuration: dict):
    configuration = SendgridConfiguration(**configuration)
    user_id = payload.get("user", {}).get("id")

    user_id = from_global_id_or_none(user_id)
    send_email(
        configuration=configuration,
        template_id=configuration.account_password_reset_template_id,
        payload=payload,
    )
    account_events.customer_password_reset_link_sent_event(user_id=user_id)


@app.task(
    autoretry_for=(SendGridException,),
    retry_backoff=CELERY_RETRY_BACKOFF,
    retry_kwargs={"max_retries": CELERY_RETRY_MAX},
    compression="zlib",
)
def send_request_email_change_email_task(payload: dict, configuration: dict):
    configuration = SendgridConfiguration(**configuration)
    user_id = payload.get("user", {}).get("id")
    send_email(
        configuration=configuration,
        template_id=configuration.account_change_email_request_template_id,
        payload=payload,
    )
    account_events.customer_email_change_request_event(
        user_id=from_global_id_or_none(user_id),
        parameters={
            "old_email": payload.get("old_email"),
            "new_email": payload["recipient_email"],
        },
    )


@app.task(
    autoretry_for=(SendGridException,),
    retry_backoff=CELERY_RETRY_BACKOFF,
    retry_kwargs={"max_retries": CELERY_RETRY_MAX},
    compression="zlib",
)
def send_user_change_email_notification_task(payload: dict, configuration: dict):
    configuration = SendgridConfiguration(**configuration)
    user_id = payload.get("user", {}).get("id")
    send_email(
        configuration=configuration,
        template_id=configuration.account_change_email_confirm_template_id,
        payload=payload,
    )
    event_parameters = {
        "old_email": payload["old_email"],
        "new_email": payload["new_email"],
    }

    account_events.customer_email_changed_event(
        user_id=from_global_id_or_none(user_id), parameters=event_parameters
    )


@app.task(
    autoretry_for=(SendGridException,),
    retry_backoff=CELERY_RETRY_BACKOFF,
    retry_kwargs={"max_retries": CELERY_RETRY_MAX},
    compression="zlib",
)
def send_account_delete_confirmation_email_task(payload: dict, configuration: dict):
    configuration = SendgridConfiguration(**configuration)
    send_email(
        configuration=configuration,
        template_id=configuration.account_delete_template_id,
        payload=payload,
    )


@app.task(
    autoretry_for=(SendGridException,),
    retry_backoff=CELERY_RETRY_BACKOFF,
    retry_kwargs={"max_retries": CELERY_RETRY_MAX},
    compression="zlib",
)
def send_set_user_password_email_task(payload: dict, configuration: dict):
    configuration = SendgridConfiguration(**configuration)
    send_email(
        configuration=configuration,
        template_id=configuration.account_set_customer_password_template_id,
        payload=payload,
    )


@app.task(
    autoretry_for=(SendGridException,),
    retry_backoff=CELERY_RETRY_BACKOFF,
    retry_kwargs={"max_retries": CELERY_RETRY_MAX},
    compression="zlib",
)
def send_email_with_dynamic_template_id(
    payload: dict, template_id: str, configuration: dict
):
    configuration = SendgridConfiguration(**configuration)
    send_email(
        configuration=configuration,
        template_id=template_id,
        payload=payload,
    )
