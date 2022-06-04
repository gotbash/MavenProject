package pageobjects;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

public class Menu {

    private WebDriver driver;

    WebElement menuTickets = driver.findElement(By.xpath("//a[@id='menu-tickets']//p"));
    WebElement menuDashboard = driver.findElement(By.xpath("//a[@id='menu-dashboard']//p"));
    WebElement menuCompanies = driver.findElement(By.xpath("//a[@id='menu-companies']//p"));
    WebElement menuContacts = driver.findElement(By.xpath("//a[@id='menu-contacts']//p"));
    WebElement menuDevices = driver.findElement(By.xpath("//a[@id='menu-device-list']//p"));
    WebElement menuDepartments = driver.findElement(By.xpath("//a[@id='menu-departments']//p"));
    WebElement menuCategories = driver.findElement(By.xpath("//a[@id='menu-categories']//p"));








}

