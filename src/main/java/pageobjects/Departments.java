package pageobjects;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

public class Departments {
    private WebElement driver;
    WebElement create_new_department = driver.findElement(By.id("new-department"));
    WebElement searchbar = driver.findElement(By.id("search-bar"));
    WebElement search = driver.findElement(By.id("department-search-title"));
    WebElement search_filter_button = driver.findElement(By.id("department-search-filter"));
    WebElement search_clear_button = driver.findElement(By.id("department-search-clear"));

}
