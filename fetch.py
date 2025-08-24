import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import logging
from datetime import datetime

# Set up logging configuration
def setup_logging():
    """Configure logging to file and console"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a timestamp for the log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/nepjol_search_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return log_filename

# Initialize logging
log_filename = setup_logging()
logger = logging.getLogger(__name__)

def search_nepjol(query):
    logger.info(f"Starting search for query: '{query}'")
    base_url = "https://www.nepjol.info/index.php/index/search/index"
    
    params = {
        "query": query,
        "dateFromYear": "",
        "dateFromMonth": "",
        "dateFromDay": "",
        "dateToYear": "",
        "dateToMonth": "",
        "dateToDay": "",
        "authors": ""
    }

    try:
        logger.debug(f"Making request to: {base_url}")
        logger.debug(f"Request parameters: {params}")
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Request successful. Status code: {response.status_code}")
        logger.debug(f"Response URL: {response.url}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("div", class_="obj_article_summary")
        
        logger.info(f"Found {len(results)} result elements")

        if not results:
            logger.warning("No results found in the parsed HTML")
            return []

        parsed_results = []
        for i, result in enumerate(results, 1):
            try:
                link_tag = result.find("a")
                title = link_tag.get_text(strip=True) if link_tag else "No title"
                link = link_tag["href"] if link_tag and link_tag.has_attr("href") else "No link"
                
                if link.startswith("/"):
                    link = "https://www.nepjol.info" + link
                    logger.debug(f"Converted relative URL to absolute: {link}")

                author_tag = result.find("div", class_="authors")
                authors = author_tag.get_text(strip=True) if author_tag else "No authors"

                source_tag = result.find("div", class_="source")
                source = source_tag.get_text(strip=True) if source_tag else "Unknown source"

                parsed_results.append({
                    "title": title,
                    "authors": authors,
                    "link": link,
                    "source": source
                })
                
                logger.debug(f"Parsed result {i}: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"Error parsing result {i}: {e}")
                continue

        logger.info(f"Successfully parsed {len(parsed_results)} results")
        return parsed_results

    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error in search_nepjol: {e}")
        return []

def display_results(results, query):
    if not results:
        logger.warning("No results to display")
        return
    
    print(f"\n{'='*80}")
    print(f"SEARCH RESULTS FOR: '{query.upper()}'")
    print(f"Found {len(results)} results")
    print(f"{'='*80}\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   Authors: {result['authors']}")
        print(f"   Source: {result['source']}")
        print(f"   Link: {result['link']}")
        print()

def save_to_file(results, query, filename=None):
    logger.info(f"Saving results to file for query: '{query}'")
    
    if not results:
        logger.warning("No results to save")
        return
    
    if not filename:
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"nepjol_results_{safe_query}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"NepJol Search Results for: {query}\n")
            f.write(f"{'='*60}\n\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"{i}. {result['title']}\n")
                f.write(f"   Authors: {result['authors']}\n")
                f.write(f"   Source: {result['source']}\n")
                f.write(f"   Link: {result['link']}\n\n")
        
        logger.info(f"Results successfully saved to: {filename}")
        print(f"Results saved to: {filename}")
        
    except Exception as e:
        logger.error(f"Error saving to file {filename}: {e}")
        print(f"Error saving file: {e}")

def find_pdf_link(article_url):
    """
    Fetches an article's page and then the PDF viewer page to find the final download link.
    """
    logger.info(f"Step 1: Looking for PDF viewer link on: {article_url}")
    
    try:
        # Step 1: Find the link to the PDF viewer page on the main article page
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Look for the link with the specific class for the PDF viewer
        pdf_viewer_link_tag = soup.find('a', class_='obj_galley_link pdf')
        
        if not pdf_viewer_link_tag or not pdf_viewer_link_tag.has_attr('href'):
            logger.warning("PDF viewer link not found on the article page.")
            return None
        
        pdf_viewer_url = urllib.parse.urljoin(article_url, pdf_viewer_link_tag['href'])
        logger.info(f"Step 2: Found PDF viewer link. Now looking for download link on: {pdf_viewer_url}")

        # Step 2: Navigate to the PDF viewer page and find the download link
        response_viewer = requests.get(pdf_viewer_url, timeout=10)
        response_viewer.raise_for_status()
        soup_viewer = BeautifulSoup(response_viewer.text, "html.parser")

        # The direct download link has a class of 'download'
        final_download_link_tag = soup_viewer.find('a', class_='download')

        if final_download_link_tag and final_download_link_tag.has_attr('href'):
            final_pdf_url = urllib.parse.urljoin(pdf_viewer_url, final_download_link_tag['href'])
            logger.info(f"Step 3: Found final PDF download link: {final_pdf_url}")
            return final_pdf_url
        
        logger.warning("Final download link not found on the viewer page.")
        return None
            
    except requests.RequestException as e:
        logger.error(f"Error fetching page: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error in find_pdf_link: {e}")
        return None

def download_file(url, filename):
    """
    Downloads a file from a given URL and saves it with a specified filename,
    handling redirects to get the final file content.
    """
    logger.info(f"Starting download from: {url}")
    logger.info(f"Target filename: {filename}")
    
    try:
        print(f"Downloading {filename}...")
        response = requests.get(url, stream=True, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        logger.debug(f"Download response status: {response.status_code}")
        content_type = response.headers.get('Content-Type', '')
        logger.debug(f"Content-Type: {content_type}")
        
        if 'application/pdf' not in content_type:
            logger.warning(f"Downloaded file is not a PDF. Content-Type: {content_type}")
            print("The downloaded file is not a PDF. Aborting.")
            return False

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        if os.path.exists(filename):
            logger.info(f"Download complete: {filename}")
            print(f"Download complete: {filename}")
            return True
        else:
            logger.error(f"File {filename} was not created after download")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Error downloading the file: {e}")
        return False
    except Exception as e:
        logger.exception(f"An error occurred during download: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("NepJol Search Program Started")
    logger.info("=" * 50)
    
    try:
        query = input("Enter your search term: ").strip()
        logger.info(f"User input query: '{query}'")
        
        if not query:
            logger.warning("Empty query entered by user")
            print("Please enter a valid search term.")
        else:
            results = search_nepjol(query)
            display_results(results, query)
            
            if results:
                while True:
                    choice = input("Enter the number of the article to view/download (or 's' to save all to file, 'q' to quit): ").strip()
                    logger.info(f"User choice: '{choice}'")
                    
                    if choice.lower() == 'q':
                        logger.info("User chose to quit")
                        break
                    elif choice.lower() == 's':
                        logger.info("User chose to save results to file")
                        save_to_file(results, query)
                        break
                    
                    try:
                        index = int(choice) - 1
                        if 0 <= index < len(results):
                            selected_article = results[index]
                            logger.info(f"Selected article index: {index}, title: {selected_article['title'][:50]}...")
                            print(f"\nSelected article: {selected_article['title']}")
                            
                            pdf_url = find_pdf_link(selected_article['link'])
                            
                            if pdf_url:
                                print(f"Found PDF link: {pdf_url}")
                                download_choice = input("Do you want to download this PDF? (y/n): ").lower()
                                logger.info(f"Download choice: '{download_choice}'")
                                
                                if download_choice in ['y', 'yes']:
                                    clean_title = "".join(c for c in selected_article['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                                    filename = f"{clean_title}.pdf"
                                    logger.info(f"Attempting to download to: {filename}")
                                    success = download_file(pdf_url, filename)
                                    if not success:
                                        logger.warning(f"Download failed for: {filename}")
                            else:
                                print("No downloadable PDF found for this article.")
                                logger.info("No PDF found for selected article")
                                
                        else:
                            logger.warning(f"Invalid article number: {choice}")
                            print("Invalid number. Please try again.")
                    except ValueError:
                        logger.warning(f"Invalid input (not a number): '{choice}'")
                        print("Invalid input. Please enter a number, 's', or 'q'.")
            
    except Exception as e:
        logger.exception(f"Unexpected error in main program: {e}")
        print(f"An unexpected error occurred: {e}")
    
    finally:
        logger.info("Program finished")
        print(f"\nProgram finished. Log file created: {log_filename}")
