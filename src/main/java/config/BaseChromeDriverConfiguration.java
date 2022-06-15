package config;

import org.junit.After;
import org.junit.Before;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;

import java.io.IOException;
public class BaseChromeDriverConfiguration {
    public static WebDriver driver;

    @Before
    public void initializeWebDriver() throws IOException {
        System.setProperty("webdriver.chrome.driver", ".src/drivers/chromedriver.exe");
        driver = new ChromeDriver();
        driver.manage().window().maximize();
        driver.get("http://176.36.27.131:8180/#/");
    }

    @After
    public void quitDriver() {
        driver.quit();
    }
}