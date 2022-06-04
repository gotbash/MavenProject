package pageobjects;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

public class Menu {

    private WebDriver driver;
    WebElement tickets = driver.findElement(By.id("menu-tickets"));
    WebElement dashboard = driver.findElement(By.id("menu-dashboard"));
    WebElement companies = driver.findElement(By.id("menu-companies"));
    WebElement contacts = driver.findElement(By.id("menu-contacts"));
    WebElement devices = driver.findElement(By.id("menu-device-list"));
    WebElement departments = driver.findElement(By.id("menu-departments"));
    WebElement managers = driver.findElement(By.id("menu-managers"));
    WebElement categories = driver.findElement(By.id("menu-categories"));
    WebElement menu_tickets = driver.findElement(By.xpath("//a[@id='menu-tickets']//p"));
    WebElement menu_dashboard = driver.findElement(By.xpath("//a[@id='menu-dashboard']//p"));
    WebElement menu_companies = driver.findElement(By.xpath("//a[@id='menu-companies']//p"));
    WebElement menu_contacts = driver.findElement(By.xpath("//a[@id='menu-contacts']//p"));
    WebElement menu_devices = driver.findElement(By.xpath("//a[@id='menu-device-list']//p"));
    WebElement menu_departments = driver.findElement(By.xpath("//a[@id='menu-departments']//p"));
    WebElement menu_categories = driver.findElement(By.xpath("//a[@id='menu-categories']//p"));








}

