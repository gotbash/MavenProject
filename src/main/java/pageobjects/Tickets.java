package pageobjects;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

public class Tickets {
    private WebElement driver;
    WebElement buttonTotal = driver.findElement(By.xpath("//a[@id='stage-total']"));
    WebElement buttonTotalSum = driver.findElement(By.xpath("//a[@id='stage-total']//span[@class='big']"));
    WebElement button_closed = driver.findElement(By.xpath("//a[@id='stage-closed']"));
    WebElement button_newticket = driver.findElement(By.xpath("//button[@id='create-new-ticket']"));
    WebElement searchbar = driver.findElement(By.xpath("//button[@id='search-bar']"));
    WebElement button_mytickets = driver.findElement(By.xpath("//button[@id='user_tickets']"));
    WebElement button_opentickets = driver.findElement(By.xpath("//button[@id='OPEN']"));
    WebElement panel_titles = driver.findElement(By.xpath("(//div[@class='main-panel'])[1]"));
    WebElement getPanel_titles = driver.findElement(By.xpath("//tbody/tr/th[string-length(text())>0]"));

}
