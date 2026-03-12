import requests
import os

companies = {
"AIRTELAFRI":"airtel.africa",
"MTNN":"mtn.ng",
"BUAFOODS":"buafoods.com",
"DANGCEM":"dangotecement.com",
"ARADEL":"aradel.com",
"SEPLAT":"seplatenergy.com",
"GTCO":"gtco.com",
"ZENITHBANK":"zenithbank.com",
"WAPCO":"lafarge.com.ng",
"PRESCO":"presco-plc.com",
"INTBREW":"intlbrew.com",
"NB":"nbplc.com",
"NESTLE":"nestle-cwa.com",
"FIRSTHOLDCO":"firstholdco.com",
"UBA":"ubagroup.com",
"STANBIC":"stanbicibtcbank.com",
"ACCESSCORP":"accesscorporation.com",
"FBNH":"fbnholdings.com",
"ETI":"ecobank.com",
"DANGSUGAR":"dangote-sugar.com",
"TRANSCORP":"transcorpgroup.com",
"GUINNESS":"guinness-nigeria.com",
"FCMB":"fcmb.com",
"NAHCO":"nahcoaviance.com",
"CUSTODIAN":"custodianplc.com.ng",
"JBERGER":"julius-berger.com",
"NGXGROUP":"ngxgroup.com",
"STERLINGNG":"sterling.ng",
"BUACEMENT":"buacement.com",
"UCAP":"unitedcapitalplcgroup.com",
"OANDO":"oandoplc.com",
"PZ":"pzcussons.com",
"MECURE":"mecure.com",
"TOTAL":"totalenergies.com",
"HONEYFLOUR":"honeywellflour.com",
"ETRANZACT":"etranzact.com",
"UNILEVER":"unilever.com",
"GEREGU":"geregu.com",
"FIDELITYBK":"fidelitybank.ng",
"CHAMS":"chamsplc.com",
"AIICO":"aiicoplc.com",
"JOHNHOLT":"johnholtplc.com",
"JAIZBANK":"jaizbankplc.com",
"FIDSON":"fidson.com",
"SKYAVN":"skywayaviationng.com"
}

folder = os.path.expanduser("~/Downloads/ngx_logos")
os.makedirs(folder, exist_ok=True)

for ticker, domain in companies.items():

    url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"

    try:
        r = requests.get(url)

        if r.status_code == 200:

            with open(f"{folder}/{ticker}.png","wb") as f:
                f.write(r.content)

            print("Saved", ticker)

        else:
            print("Failed:", ticker)

    except Exception as e:
        print("Error:", ticker, e)