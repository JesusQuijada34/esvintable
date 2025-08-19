# @JesusQuijada34 | @jq34_channel | @jq34_group
# PyScript Recreado de Trebel

# ====================
# LIBRARIES
# ====================
import requests, sys, cloudscraper

# ====================
# VARIABLES
# ====================
b = "\033[96m"
g = "\033[92m"
y = "\033[93m"
r = "\033[91m"
ma = "\033[95m"
re = "\033[0m"
banner = f"""{r}=================================\n|{g} ESVINTABLE - Trebel esVint.v2 {r}|\n================================="""
providers = ['Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire', 'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize']

# ====================
# FUNCTIONS
# ====================
def getcIP():
    cIP = requests.get('https://ipinfo.io/json').json()
    ctry = cIP['country']
    return ctryS

def dl(isrc):
    s = cloudscraper.create_scraper()
    t = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI" # it can be obtained from the 'Trebel' application requests
    for provider in providers:
        ep = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}" # https://mds.projectcarmen.com/stream/preview?provider={provider}&isrc={isrc} ==> preview | https://cfs.projectcarmen.com/tracks/{isrc}.64.m4a?provider=SonyMusic ==> IDK
        h = {
        "Authorization": f"Bearer {t}"
        }
        print(f"{b}creating request API for {provider}...")
        try:
            r = s.get(ep, headers=h)
            if r.status_code == 200:
                fn = f"op/{isrc}.m4a"
                with open(fn, "wb") as o:
                    o.write(r.content)
                print(f"{g}file has saved as: {fn}\n")
                return True
            else:
                print(f"{r}provider status lead {provider} : {r.status_code} - {r.text}")
        except requests.exceptions.RequestException as o:
            print(f"{r}request library was failed for provider in '{provider}' : {o}")
    return False

def m():
    i = input(f"{ma}ISRC: ").strip()
    if not i:
        print(f"{y}char not defined!")
        return
    cip = getcIP()
    if cip == "US":
        dl(i)

    else:
        print(f"{r}VPN or Proxy for: 'US' (country field)!")
        sys.exit()

# ====================
# STARTER MODULE
# ====================
if __name__ == "__main__":
    print(banner)
    m()

# @JesusQuijada34 | @jq34_channel | @jq34_group
# Remix from: @SiMijoSiManda | @simijosimethodleaks
# Github: github.com/JesusQuijada34/esvintable/
