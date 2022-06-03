package pageobjects;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

public class Menu {

    WebElement tickets = driver.findElement(By.id("menu-tickets"));
    WebElement dashboard = driver.findElement(By.id("menu-dashboard"));
    WebElement companies = driver.findElement(By.id("menu-companies"));
    WebElement contacts = driver.findElement(By.id("menu-contacts"));
    WebElement devices = driver.findElement(By.id("menu-device-list"));
    WebElement departments = driver.findElement(By.id("menu-departments"));
    WebElement managers = driver.findElement(By.id("menu-managers"));
    WebElement categories = driver.findElement(By.id("menu-categories"));


    //a[@id='menu-dashboard']
    //a[@id='menu-tickets']
    //a[@id='menu-companies']
    //a[@id='menu-contacts']
    //a[@id='menu-device-list']
    //a[@id='menu-departments']
    //a[@id='menu-managers']
    //a[@id='menu-categories']

    // Pages

    WebElement total_button = driver.findElement(By.id("stage-total"));
    //a[@id='stage-total']
    WebElement closed_button = driver.findElement(By.id("stage-closed"));
    //a[@id='stage-closed']
    WebElement NewTicket = driver.findElement(By.id("create-new-ticket"));
    //button[@id='create-new-ticket']
    WebElement search_bar = driver.findElement(By.id("search-bar"));
    //input[@id='search-bar']

}
