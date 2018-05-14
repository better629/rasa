from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy
import logging
from collections import namedtuple

from typing import Text, List, Dict, Any, Optional

from rasa_core.channels import OutputChannel
from rasa_core.domain import Domain

logger = logging.getLogger(__name__)


class Element(dict):
    __acceptable_keys = ['title', 'item_url', 'image_url',
                         'subtitle', 'buttons']

    def __init__(self, *args, **kwargs):
        kwargs = {key: value
                  for key, value in kwargs.items()
                  if key in self.__acceptable_keys}

        super(Element, self).__init__(*args, **kwargs)


BotMessage = namedtuple("BotMessage", "text data")


class Button(dict):
    pass


class Dispatcher(object):
    """Send messages back to user"""

    def __init__(self, sender_id, output_channel, domain):
        # type: (Text, OutputChannel, Domain) -> None

        self.sender_id = sender_id
        self.output_channel = output_channel
        self.domain = domain
        self.send_messages = []
        self.latest_bot_messages = []

    # TODO: this should really be done at the channel level
    def utter_response(self, message):
        # type: (Dict[Text, Any]) -> None
        """Send a message to the client."""

        if message.get("elements"):
            self.utter_custom_message(message.get("elements"))

        elif message.get("buttons"):
            self.utter_button_message(message.get("text"),
                                      message.get("buttons"))
        else:
            self.utter_message(message.get("text"))

        # if there is an image we handle it separately as an attachment
        if message.get("image"):
            self.utter_attachment(message.get("image"))

    # TODO: this should really be done at the channel level
    def utter_message(self, text):
        # type: (Text) -> None
        """"Send a text to the output channel"""

        self.latest_bot_messages.append(BotMessage(text=text,
                                                   data=None))
        if self.sender_id is not None and self.output_channel is not None:
            for message_part in text.split("\n\n"):
                self.output_channel.send_text_message(self.sender_id,
                                                      message_part)
                self.send_messages.append(message_part)

    def utter_custom_message(self, *elements):
        # type: (*Dict[Text, Any]) -> None
        """Sends a message with custom elements to the output channel."""

        bot_message = BotMessage(text=None,
                                 data={"elements": elements})
        self.latest_bot_messages.append(bot_message)
        self.output_channel.send_custom_message(self.sender_id, elements)

    def utter_button_message(self, text, buttons, **kwargs):
        # type: (Text, List[Dict[Text, Any]], **Any) -> None
        """Sends a message with buttons to the output channel."""
        self.latest_bot_messages.append(BotMessage(text=text,
                                                   data={"buttons": buttons}))
        self.output_channel.send_text_with_buttons(self.sender_id, text,
                                                   buttons,
                                                   **kwargs)

    def utter_attachment(self, attachment):
        # type: (Text) -> None
        """Send a message to the client with attachments."""

        bot_message = BotMessage(text=None,
                                 data={"attachment": attachment})
        self.latest_bot_messages.append(bot_message)
        self.output_channel.send_image_url(self.sender_id, attachment)

    # TODO: deprecate this function
    def utter_button_template(self, template, buttons,
                              filled_slots=None,
                              silent_fail=False,
                              **kwargs):
        # type: (Text, List[Dict[Text, Any]], **Any) -> None
        """Sends a message template with buttons to the output channel."""

        message = self._generate_response(template,
                                          filled_slots,
                                          silent_fail,
                                          **kwargs)
        if not message:
            return

        if "buttons" not in message:
            message["buttons"] = buttons
        else:
            message["buttons"].extend(buttons)
        self.utter_response(message)

    def utter_template(self,
                       template,  # type: Text
                       filled_slots=None,  # type: Optional[Dict[Text, Text]]
                       silent_fail=False,  # type: bool
                       **kwargs  # type: ** Any
                       ):
        # type: (...) -> None
        """"Send a message to the client based on a template."""

        message = self._generate_response(template,
                                          filled_slots,
                                          silent_fail,
                                          **kwargs)

        if not message:
            return

        self.utter_response(message)

    def _generate_response(
            self,
            template,  # type: Text
            filled_slots=None,  # type: Optional[Dict[Text, Text]]
            silent_fail=False,  # type: bool
            **kwargs  # type: ** Any
    ):
        # type: (...) -> Dict[Text, Any]
        """"Generate a response."""

        message = self.domain.nlg.generate(template, filled_slots, **kwargs)

        if message is None and not silent_fail:
            raise ValueError("Couldn't create message for template '{}'."
                             "".format(template))

        return message
