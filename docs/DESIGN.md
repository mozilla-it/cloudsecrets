# Design

The design of this project is presently broken into 2 pieces:

1. A data scraper
2. A dash board for data presentation

## The Data Scraper

The data scraper (scraper for short) is designed to "scrape" data from the Cloudsnap
web pages.  The scraped data will allow us to produce dashboards to allow for actionable
insights of issues that teams upstream can more effectively address.  The scraped data
will be produced in raw format in a consumable report by itself (CSV for example).  The raw
data itself will not be cleaned, have outliers removed, etc at this stage.

## The Dashboard

The dashboard will present a mechanism by which a finance team member may see, address, and acknowledge an issue in a fashion that presents a higher signal-to-noise ratio that we presently see in the Cloudsnap dashboard.  While this will be fully productionized as part of this work, it is hoped that we can pitch this to Cloudsnap as an improvement to their product
and they can integrate over time on our behalf reducing the maintaince burden.

## Author(s)

Stewart Henderson <shenderson@mozilla.com>
