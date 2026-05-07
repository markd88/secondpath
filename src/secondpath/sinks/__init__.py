"""Built-in sinks."""

from secondpath.sinks.basic import MessageQueueSink, SlackSink, SqliteSink, StdoutSink, WebhookSink

__all__ = ["MessageQueueSink", "SlackSink", "SqliteSink", "StdoutSink", "WebhookSink"]
