package config;

import org.junit.Test;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;

public class BaseChromeDriverConfiguration {
    @Test
    public void launchBrowser() {
        System.setProperty("webdriver.chrome.driver", "chromedriver.exe");
        WebDriver driver = new ChromeDriver();
        driver.get("http://176.36.27.131:8180/#/");
        driver.quit();
    }
}