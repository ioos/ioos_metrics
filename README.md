# ioos_by_the_numbers
Working on creating metrics for the [IOOS by the numbers](https://ioos.noaa.gov/about/ioos-by-the-numbers/)

Requirements:


## Website
Leveraged existing resources from https://github.com/noaa-fisheries-integrated-toolbox/toolbox_web_templating.

The webpages are built from the `website/` directory.

| File(s)                               | Description
|---------------------------------------|---------------------------------------------------------------
| `*_config.json`                       | configuration for what resources to present on the webpages.
| `create_asset_inventory_page.py`      | script to create https://ioos.github.io/ioos_metrics/asset_inventory.html
| `create_gts_atn_page.py`              | script to create https://ioos.github.io/ioos_metrics/gts_atn.html
| `create_gts_regional_landing_page.py` | script to create https://ioos.github.io/ioos_metrics/gts_regional.html
| `deploy/index.html`                   | html source for landing page https://ioos.github.io/ioos_metrics/index.html
| `deploy/static/main.css`              | css control for website.

## Development

To create the webpages on your local system
```bash
git clone https://github.com/ioos/ioos_metrics.git
cd ioos_metrics/website
python create_asset_inventory_page.py
python create_gts_atn_landing_page.py
python create_gts_regional_landing_page.py
```

All the webpages will be saved to `website/deploy`. You can view the local html files with a web browser for testing.

## Deployment

The website is generated using GitHub Actions and GitHub Pages. The python scripts, referenced above, are ran and the
directory `website/deploy` is then uploaded as an artifact for GitHub Pages to serve as a website.
This process is automatically ran with every push to the `main` branch. See [here](https://github.com/ioos/ioos_metrics/blob/main/.github/workflows/website_create_and_deploy.yml).
