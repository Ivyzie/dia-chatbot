import asyncio
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

# 1) Specify your target URLs here:
urls = [
    "https://www.carlist.my/faq#"
    
]

async def scrape_and_save(urls, output_dir):
    # 2) Crawler configuration
    config = CrawlerRunConfig(
        excluded_tags=['header', 'footer', 'nav', 'section.article-relatives'],
        word_count_threshold=10,
        exclude_external_links=True,
        exclude_social_media_links=True
    )

    # 3) Make sure output_dir exists
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "content.md")

    async with AsyncWebCrawler() as crawler:
        # Open the combined file once
        with open(out_path, 'w', encoding='utf-8') as out_file:
            for url in urls:
                print(f"Scraping: {url}")
                result = await crawler.arun(url, config=config)

                if result.markdown:
                    chunk = result.markdown + "\n\n"
                else:
                    chunk = f"No markdown content found for {url}\n\n"

                out_file.write(f"## {url}\n\n")
                out_file.write(chunk)
                print(f"Appended content for {url}")

    print(f"\n✅ All content written to {out_path}")

if __name__ == "__main__":
    # 4) Compute output directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")

    # 5) Run the crawler
    asyncio.run(scrape_and_save(urls, output_dir))
