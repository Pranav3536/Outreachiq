"""Email tools: templates, placeholders, attachments, campaign prep, SMTP."""
from .attachments import (
    MAX_RESUME_BYTES,
    build_attachment,
    delete_resume,
    get_resume_path,
    resume_exists,
    resume_meta,
    save_resume,
    validate_resume,
)
from .campaign_prep import PreparedCampaign, RecipientResult, prepare_campaign
from .message_builder import MessageBuildError, build_message
from .placeholders import (
    FALLBACKS,
    RenderResult,
    TemplateError,
    ensure_sendable,
    find_placeholders,
    render,
    render_for_contact,
    validate_template,
)
from .smtp_config import SmtpConfig, SmtpConfigError, credentials_status, load_smtp_config
from .smtp_sender import (
    STATUS_ACCEPTED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SIMULATED,
    STATUS_UNKNOWN,
    SendResult,
    run_batch,
    send_one,
)
from .templates import (
    DEFAULT_BODY,
    DEFAULT_SUBJECT,
    delete_template,
    list_templates,
    load_template,
    load_working,
    save_template,
    save_working,
)

__all__ = [
    # attachments
    "MAX_RESUME_BYTES", "build_attachment", "delete_resume", "get_resume_path",
    "resume_exists", "resume_meta", "save_resume", "validate_resume",
    # campaign_prep
    "PreparedCampaign", "RecipientResult", "prepare_campaign",
    # message_builder
    "MessageBuildError", "build_message",
    # placeholders
    "FALLBACKS", "RenderResult", "TemplateError",
    "ensure_sendable", "find_placeholders", "render",
    "render_for_contact", "validate_template",
    # smtp_config
    "SmtpConfig", "SmtpConfigError", "credentials_status", "load_smtp_config",
    # smtp_sender
    "STATUS_ACCEPTED", "STATUS_FAILED", "STATUS_PENDING",
    "STATUS_SIMULATED", "STATUS_UNKNOWN",
    "SendResult", "run_batch", "send_one",
    # templates
    "DEFAULT_BODY", "DEFAULT_SUBJECT",
    "delete_template", "list_templates", "load_template",
    "load_working", "save_template", "save_working",
]
