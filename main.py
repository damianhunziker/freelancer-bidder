import pyperclip
import webbrowser

def copy_text_and_open_link():
    # Text you want to copy to the clipboard
    bid_teaser_text = "This is the bid teaser text that will be copied to the clipboard."
    # URL you want to open
    job_url = "https://www.freelancer.com/projects/39231464"

    input("Press Enter to copy the bid teaser text to the clipboard and open the job link...")

    # Copy text to clipboard
    pyperclip.copy(bid_teaser_text)
    print("Bid teaser text copied to clipboard!")

    # Open the URL in the default browser
    webbrowser.open(job_url)
    print("Web browser opened to the job link.")

if __name__ == "__main__":
    copy_text_and_open_link() 