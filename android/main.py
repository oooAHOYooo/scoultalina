from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout


KV = """
<RootLayout>:
    orientation: 'vertical'
    Label:
        text: 'ScoutAlina (Android) - TODO: Implement GPS discovery'
    Button:
        text: 'Sync Now'
        on_release: app.sync_now()
"""


class RootLayout(BoxLayout):
    pass


class ScoutAlinaApp(App):
    def build(self):
        Builder.load_string(KV)
        return RootLayout()

    def sync_now(self):
        # TODO: implement sync with backend
        print("[sync] TODO: implement backend sync")


if __name__ == "__main__":
    ScoutAlinaApp().run()


