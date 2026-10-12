"""The languages Yuki supports.

Calls: SupportedLanguages.
"""

from yuki_sdk import LanguageSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

languages = LanguageSet(yuki_cred)
languages.get()
for language in languages:
    print(f"{language.code}  {language.description}  {language.native_description}")
